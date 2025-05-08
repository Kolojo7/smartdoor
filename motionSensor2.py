import RPi.GPIO as GPIO
import threading
import time

GPIO.setmode(GPIO.BCM)
PIR_PIN = 22
GPIO.setup(PIR_PIN, GPIO.IN)

motionStatus = False  # This gets updated continuously

def _watch_motion():
    global motionStatus
    while True:
        motionStatus = GPIO.input(PIR_PIN)
        time.sleep(0.1)

_thread = threading.Thread(target=_watch_motion, daemon=True)
_thread.start()