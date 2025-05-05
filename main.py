
from smartdoor import setup_gpio, open_lock, close_lock, start_flashlight, stop_flashlight, neo
from aws_sync import fetch_override_status, upload_log_and_status
from awsStream import setup_stream_gpio, start_stream, stream_instance
import asyncio
from face_rec_aws import face_rec
from motionSensor import setup_motion_sensor, get_motion_status
import RPi.GPIO as GPIO
import time
import json
import os

# --- Constants ---
LAST_OVERRIDE_FILE = "/home/pi/smartdoor/last_override.json"
BUTTON_PIN = 27  # Button pin for reboot
HOLD_TIME_REQUIRED = 5  # Seconds the button must be held

# --- Functions ---
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

def check_reboot_button():
    if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
        press_start = time.time()
        while GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            time.sleep(0.1)
            if time.time() - press_start >= HOLD_TIME_REQUIRED:
                print("[INFO] Rebooting system due to button press.")
                os.system("sudo reboot")
                break

def main():
    time.sleep(2)
    setup_gpio()
    setup_motion_sensor()
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    asyncio.get_event_loop().create_task(start_stream())
    last_override = load_last_override()
    first_run = True
    start_flashlight()

    try:
        while True:
            check_reboot_button()

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
                    if get_motion_status():
                        if stream_instance:
                            stream_instance.pause()
                            time.sleep(0.5)  # Let camera settle
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
                finally:
                    if stream_instance:
                        stream_instance.resume()

            time.sleep(3)

    except KeyboardInterrupt:
        print("[EXIT] KeyboardInterrupt received. Cleaning up...")

    finally:
        stop_flashlight()

        # Flash the LED ring to indicate shutdown
        for _ in range(2):
            neo.fill_strip(0, 0, 50)
            neo.update_strip()
            time.sleep(0.3)
            neo.fill_strip(0, 0, 0)
            neo.update_strip()
            time.sleep(0.3)

        GPIO.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
