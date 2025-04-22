import time
import board
import busio
import threading
import RPi.GPIO as GPIO
from adafruit_veml7700 import VEML7700
from pi5neo import Pi5Neo

LUX_THRESHOLD = 40
RELAY_PIN = 17
LED_BRIGHTNESS = 50

neo = Pi5Neo('/dev/spidev0.0', 1000, 800)
neo.fill_strip(0, 0, 0)
neo.update_strip()

i2c = busio.I2C(board.SCL, board.SDA)
veml7700 = VEML7700(i2c, address=0x10)
veml7700.light_gain = 1
veml7700.integration_time = 100

GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(RELAY_PIN, GPIO.OUT)
    GPIO.output(RELAY_PIN, GPIO.HIGH)

def open_lock():
    GPIO.output(RELAY_PIN, GPIO.LOW)
    print("Lock OPEN")

def close_lock():
    GPIO.output(RELAY_PIN, GPIO.HIGH)
    print("Lock CLOSED")

flashlight_active = False
flashlight_thread = None

def flashlight_loop(threshold=LUX_THRESHOLD):
    global flashlight_active
    leds_on = False

    while flashlight_active:
        lux = veml7700.lux
        if lux < threshold and not leds_on:
            neo.fill_strip(LED_BRIGHTNESS, LED_BRIGHTNESS, LED_BRIGHTNESS)
            neo.update_strip()
            leds_on = True
        elif lux >= threshold and leds_on:
            neo.fill_strip(0, 0, 0)
            neo.update_strip()
            leds_on = False
        time.sleep(0.5)

def start_flashlight(threshold=LUX_THRESHOLD):
    global flashlight_active, flashlight_thread
    flashlight_active = True
    flashlight_thread = threading.Thread(target=flashlight_loop, args=(threshold,))
    flashlight_thread.start()

def stop_flashlight():
    global flashlight_active, flashlight_thread
    flashlight_active = False
    if flashlight_thread:
        flashlight_thread.join()
    neo.fill_strip(0, 0, 0)
    neo.update_strip()
