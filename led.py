import time
import board
import busio
import RPi.GPIO as GPIO
from adafruit_veml7700 import VEML7700
from pi5neo import Pi5Neo

# --- Constants ---
LUX_THRESHOLD = 200  # Light threshold for triggering scan + lock
RELAY_PIN = 17      # GPIO pin for solenoid lock
LED_BRIGHTNESS = 100  # Adjust for comfortable brightness

# --- Setup LED ring ---
neo = Pi5Neo('/dev/spidev0.0', 241, 800)
neo.fill_strip(0, 0, 0)
neo.update_strip()

# --- Setup light sensor ---
i2c = busio.I2C(board.SCL, board.SDA)
veml7700 = VEML7700(i2c, address=0x10)
veml7700.light_gain = 1
veml7700.integration_time = 100

# --- Setup GPIO for lock ---
GPIO.setmode(GPIO.BCM)
GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.output(RELAY_PIN, GPIO.LOW)  # Start with lock OFF

# --- State flag ---
leds_on = False

try:
    while True:
        lux = veml7700.lux
        print(f"Ambient Light Level: {lux:.2f} lux")

        if lux < LUX_THRESHOLD and not leds_on:
            # It's dark - light face + open lock
            neo.fill_strip(LED_BRIGHTNESS, LED_BRIGHTNESS, LED_BRIGHTNESS)
            neo.update_strip()
            GPIO.output(RELAY_PIN, GPIO.HIGH)
            print("LEDs ON , Lock OPEN")
            leds_on = True

        elif lux >= LUX_THRESHOLD and leds_on:
            # It's bright - turn off LEDs + close lock
            neo.fill_strip(0, 0, 0)
            neo.update_strip()
            GPIO.output(RELAY_PIN, GPIO.LOW)
            print("LEDs OFF, Lock CLOSED")
            leds_on = False

        time.sleep(1)

except KeyboardInterrupt:
    print("Exiting program.")
    neo.fill_strip(0, 0, 0)
    neo.update_strip()
    GPIO.output(RELAY_PIN, GPIO.LOW)
    GPIO.cleanup()
