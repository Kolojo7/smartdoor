import RPi.GPIO as GPIO
import time

#GPIO
GPIO.setmode(GPIO.BCM)
PIR_PIN = 22
GPIO.setup(PIR_PIN, GPIO.IN)

#Global var call
motionStatus = False

def watch_motion():
    global motionStatus
    while True:
        motionStatus = GPIO.input(PIR_PIN)
        time.sleep(0.1)  #poll per 100ms
