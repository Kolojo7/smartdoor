import RPi.GPIO as GPIO
import threading
import time

PIR_PIN = 22
motionStatus = False
lock = threading.Lock()

def setup_motion_sensor():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIR_PIN, GPIO.IN)

    def _watch_motion():
        global motionStatus
        while True:
            with lock:
                motionStatus = GPIO.input(PIR_PIN)
            time.sleep(0.1)

    _thread = threading.Thread(target=_watch_motion, daemon=True)
    _thread.start()

def get_motion_status():
    with lock:
        return motionStatus
