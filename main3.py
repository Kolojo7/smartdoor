# --- main.py ---
from smartdoor import setup_gpio, open_lock, close_lock, start_flashlight, stop_flashlight, neo
from aws_sync import fetch_override_status, upload_log_and_status
from motionSensor import setup_motion_sensor, get_motion_status
from awsStream import start_streaming_thread
import time
import RPi.GPIO as GPIO
import json
import os
import threading

LAST_OVERRIDE_FILE = "/home/pi/smartdoor/last_override.json"

# --- Reboot Button Watchdog Thread ---
def start_button_watchdog():
    BUTTON_PIN = 27
    HOLD_TIME = 5  # seconds

    # GPIO is already set in setup_gpio() to PUD_DOWN

    def watchdog_loop():
        print("[BUTTON] Reboot watchdog running...")
        try:
            while True:
                if GPIO.input(BUTTON_PIN) == GPIO.HIGH:  # ← Button pressed (HIGH)
                    press_start = time.time()
                    print("[BUTTON] Detected press.")
                    while GPIO.input(BUTTON_PIN) == GPIO.HIGH:
                        time.sleep(0.1)
                        if time.time() - press_start >= HOLD_TIME:
                            print("[BUTTON] Reboot triggered!")
                            os.sync()
                            os.system("sudo /sbin/reboot -f &")
                            return
                time.sleep(0.1)
        except Exception as e:
            print(f"[BUTTON] Error: {e}")
    threading.Thread(target=watchdog_loop, daemon=True).start()

# --- Helpers for manual override ---
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

# --- Main entrypoint ---
def main():
    setup_gpio()                # ✅ Set GPIO mode and input pins
    start_button_watchdog()     # ✅ Start reboot thread after GPIO is ready
    setup_motion_sensor()       # ✅ Start PIR motion monitoring
    last_override = load_last_override()
    first_run = True
    start_flashlight()          # ✅ Start ambient light LED controller

    start_streaming_thread(get_motion_status)  # ✅ Begin RealSense stream + event recorder

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
