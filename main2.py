
from face_rec_aws import get_shared_pipeline, stop_shared_pipeline

def recognize_face():
    try:
        print("[INFO] Starting face recognition...")
        pipeline = get_shared_pipeline()
        frames = pipeline.wait_for_frames()
        color_frame = frames.get_color_frame()
        if not color_frame:
            print("[ERROR] No frame captured for recognition.")
            return False

        color_image = np.asanyarray(color_frame.get_data())
        locs, names = recognize_faces(color_image)
        
        if AUTHORIZED_USER in names:
            print(f"[SUCCESS] Face recognized: {AUTHORIZED_USER}")
            return True
        else:
            print("[FAILURE] No authorized face recognized.")
            return False

    except Exception as e:
        print(f"[ERROR] Face recognition failed: {e}")
        return False

from smartdoor import setup_gpio, open_lock, close_lock, start_flashlight, stop_flashlight, neo
from aws_sync import fetch_override_status, upload_log_and_status
from motionSensor import setup_motion_sensor, get_motion_status
from camera import start_streaming, stop_streaming, resume_streaming, recognize_face
import time
import RPi.GPIO as GPIO
import json
import os
import threading

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

def start_button_watchdog():
    BUTTON_PIN = 27
    HOLD_TIME = 5

    def watchdog_loop():
        print("[BUTTON] Reboot watchdog running...")
        try:
            while True:
                if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
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

def flash_led(color: str):
    if color == "green":
        r, g, b = 0, 255, 0
    elif color == "red":
        r, g, b = 255, 0, 0
    else:
        return
    neo.fill_strip(r, g, b)
    neo.update_strip()
    time.sleep(2)
    neo.fill_strip(0, 0, 0)
    neo.update_strip()

def main():
    setup_gpio()
    start_button_watchdog()
    setup_motion_sensor()
    last_override = load_last_override()
    first_run = True
    start_flashlight()
    start_streaming(get_motion_status)

    try:
        while True:
            override = fetch_override_status()

            if first_run or override != last_override:
                reason = "initial boot" if first_run else "value changed"
                print(f"[OVERRIDE APPLIED] Reason: {reason}. override={{override}}, last_override={{last_override}}")
                if override:
                    close_lock()
                    upload_log_and_status(f"Lock ON (manual override - {{reason}})", True)
                else:
                    open_lock()
                    upload_log_and_status(f"Lock OFF (manual override - {{reason}})", False)
                last_override = override
                save_last_override(last_override)
                first_run = False

            else:
                if get_motion_status():
                    print("[MOTION] Movement detected.")
                    upload_log_and_status("Motion detected. Starting face recognition...", None)

                    try:
                        # stop_streaming() now handled by shared pipeline
                        time.sleep(1)

                        if recognize_face():
                            open_lock()
                            upload_log_and_status("Lock OFF (face scan)", False)
                            flash_led("green")
                            last_override = False
                            save_last_override(last_override)
                        else:
                            close_lock()
                            upload_log_and_status("Lock ON (face scan)", True)
                            flash_led("red")
                            last_override = True
                            save_last_override(last_override)
                    except Exception as e:
                        print(f"[WARNING] face_rec() failed: {{e}}. Continuing loop.")
                    finally:
                        # resume_streaming() now handled by shared pipeline
                else:
                    print("[INFO] No override change. Streaming and monitoring...")

            time.sleep(3)

    except KeyboardInterrupt:
        print("[EXIT] KeyboardInterrupt received. Cleaning up.")
    finally:
        stop_flashlight()
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
