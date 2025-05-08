# --- main.py ---
from smartdoor import setup_gpio, open_lock, close_lock, start_flashlight, stop_flashlight, neo
from aws_sync import fetch_override_status, upload_log_and_status
from face_rec_aws import face_rec
from motionSensor2 import motionStatus
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
    last_override = load_last_override()
    first_run = True
    start_flashlight()  # Start once and leave running

    if motionStatus:
        print("[MOTION] Movement detected.")

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
                print("[INFO] No override change. Proceeding with face recognition...")
                upload_log_and_status("No override change. Using face recognition.", None)
                try:
                    if face_rec():
                        open_lock()
                        upload_log_and_status("Lock OFF (face scan)", False)
                        last_override = False
                        save_last_override(last_override)
                    else:
                        close_lock()
                        upload_log_and_status("Lock ON (face scan)", True)
                        last_override = True
                        save_last_override(last_override)
                except Exception as e:
                    print(f"[WARNING] face_rec() failed: {e}. Continuing loop.")

            time.sleep(3)

    except KeyboardInterrupt:
        print("[EXIT] KeyboardInterrupt received. Stopping flashlight and cleaning up GPIO.")
    finally:
        stop_flashlight()

        # Flash the LED ring briefly to indicate shutdown
        for _ in range(2):
            neo.fill_strip(0, 0, 255)  # GBR
            neo.update_strip()
            time.sleep(0.3)
            neo.fill_strip(0, 0, 0)
            neo.update_strip()
            time.sleep(0.3)

        GPIO.cleanup()

if __name__ == "__main__":
    main()
