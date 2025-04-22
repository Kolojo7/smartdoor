import RPi.GPIO as GPIO
import time
import os

# use BCM pin numbers
GPIO.setmode(GPIO.BCM)

# set pin 18 as input with pull-down
BUTTON_PIN = 18
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

hold_time_required = 5  # seconds to hold before reboot

try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.HIGH:
            press_start = time.time()
            while GPIO.input(BUTTON_PIN) == GPIO.HIGH:
                time.sleep(0.1)
                if time.time() - press_start >= hold_time_required:
                    print("Rebooting...")
                    os.system("sudo reboot")
                    break
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Stopped.")

finally:
    GPIO.cleanup()
