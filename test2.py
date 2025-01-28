import time
import board
import busio
import RPi.GPIO as GPIO
from adafruit_veml7700 import VEML7700

# Set up GPIO mode for relay and LED control
GPIO.setmode(GPIO.BCM)
relay_pin = 17  # GPIO pin to control the relay
GPIO.setup(relay_pin, GPIO.OUT)

# Initialize the I2C bus for the lux sensor
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize the VEML7700 sensor
veml7700 = VEML7700(i2c)

# Optional: Adjust sensor settings
veml7700.light_gain = 1  # Default gain
veml7700.integration_time = 100  # Default integration time (100ms)

# Set a lux threshold to turn the LED on (adjust based on your environment)
lux_threshold = 100  # Adjust this value based on your desired light threshold

# Function to turn on the relay (LED on)
def turn_on_led():
    GPIO.output(relay_pin, GPIO.HIGH)  # This will close the relay and power the LED

# Function to turn off the relay (LED off)
def turn_off_led():
    GPIO.output(relay_pin, GPIO.LOW)  # This will open the relay and turn off the LED

# Output light readings and control the LED in a loop
try:
    while True:
        lux = veml7700.lux  # Get the current lux reading
        print(f"Ambient Light Level: {lux:.2f} lux")
        
        # Check if the lux value exceeds the threshold
        if lux > lux_threshold:
            turn_on_led()  # Turn on the LED if lux value is above the threshold
            print("LED On - Light level is high")
        else:
            turn_off_led()  # Turn off the LED if lux value is below the threshold
            print("LED Off - Light level is low")

        time.sleep(1)  # Wait 1 second before reading the sensor again

except KeyboardInterrupt:
    print("Exiting program.")

finally:
    GPIO.cleanup()  # Clean up GPIO before exiting
