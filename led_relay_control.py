import RPi.GPIO as GPIO
import time

# Set up GPIO mode
GPIO.setmode(GPIO.BCM)

# Pin Definitions
relay_pin = 17  # Change this to the GPIO pin you're using to control the relay

# Set up the GPIO pin for the relay
GPIO.setup(relay_pin, GPIO.OUT)

# Function to turn on the relay (LED on)
def turn_on_led():
    GPIO.output(relay_pin, GPIO.HIGH)  # This will close the relay and power the LED

# Function to turn off the relay (LED off)
def turn_off_led():
    GPIO.output(relay_pin, GPIO.LOW)  # This will open the relay and turn off the LED

# Main loop to blink the LED every second
try:
    while True:
        turn_on_led()  # Turn the LED on
        print("LED On")
        time.sleep(1)  # Wait for 1 second

        turn_off_led()  # Turn the LED off
        print("LED Off")
        time.sleep(1)  # Wait for 1 second

except KeyboardInterrupt:
    print("Program exited")

finally:
    GPIO.cleanup()  # Clean up GPIO pins before exiting
