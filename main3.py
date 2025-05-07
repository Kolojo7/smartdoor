# --- main.py ---
from smartdoor import setup_gpio, open_lock, close_lock, start_flashlight, stop_flashlight, neo
from aws_sync import fetch_override_status, upload_log_and_status
from motionSensor import setup_motion_sensor, get_motion_status
from awsStream import start_streaming_thread
import time
import RPi.GPIO as GPIO
import json
import os

LAST_OVERRIDE_FILE = "/home/pi/smartdoor/last_override.json"

def load_last_override():
    if os.path.exists(LAST_OVERRIDE_FILE):
        try:
            with open(LAST_OVERRIDE_FILE, "r") as f:
                data = json.load(f)
                return data.get("last_override")
        except Exception as e:
            print(f"[WARN] Could not read last_override file: {e}")
    return None

def save_last_override(value):
    try:
        with open(LAST_OVERRIDE_FILE, "w") as f:
            json.dump({"last_override": value}, f)
    except Exception as e:
        print(f"[WARN] Could not save last_override file: {e}")

def main():
    setup_gpio()
    setup_motion_sensor()  # ✅ Start background thread to monitor PIR motion
    last_override = load_last_override()
    first_run = True
    start_flashlight()

    # ✅ Start the streaming thread, pass motion detection function
    start_streaming_thread(get_motion_status)

    try:
        while True:
            override = fetch_override_status()

            if first_run or override != last_override:
                reason = "initial boot" if first_run else "value changed"
                print(f"[OVERRIDE APPLIED] Reason: {reason}. override={override}, last_override={last_override}")
                if override:
                    close_lock()
                    upload_log_and_status(f"Lock ON (manual override - {reason})", True)
                else:
                    open_lock()
                    upload_log_and_status(f"Lock OFF (manual override - {reason})", False)
                last_override = override
                save_last_override(last_override)
                first_run = False
            else:
                print("[INFO] No override change. Streaming and monitoring...")

            time.sleep(3)

    except KeyboardInterrupt:
        print("[EXIT] KeyboardInterrupt received. Stopping flashlight and cleaning up GPIO.")
    finally:
        stop_flashlight()

        # Flash LED ring briefly to indicate shutdown
        for _ in range(2):
            neo.fill_strip(0, 0, 255)
            neo.update_strip()
            time.sleep(0.3)
            neo.fill_strip(0, 0, 0)
            neo.update_strip()
            time.sleep(0.3)

        GPIO.cleanup()

if __name__ == "__main__":
    main()
