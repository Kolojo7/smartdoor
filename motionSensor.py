import RPi.GPIO as GPIO
import time

#GPIO
PIR_PIN = 22
GPIO.setup(PIR_PIN, GPIO.IN)

#Global var call
motionStatus = False

def watch_motion():
    global motionStatus
    motionStatus = GPIO.input(PIR_PIN)
    if motionStatus:
        print(f"Motion detected!")
