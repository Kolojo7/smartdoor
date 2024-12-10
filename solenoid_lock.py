import RPi.GPIO as GPIO
import time

#GPIO Pin where the relay IN is connected
RELAY_PIN = 17

GPIO Setup
GPIO.setmode(GPIO.BCM)  # Use BCM numbering
GPIO.setup(RELAY_PIN, GPIO.OUT)  # Set the relay pin as an output

try:
    while True:
        # Turn the solenoid lock ON
        GPIO.output(RELAY_PIN, GPIO.HIGH)
        print("Lock ON")
        time.sleep(5)  # Keep the lock ON for 5 seconds

        # Turn the solenoid lock OFF
        GPIO.output(RELAY_PIN, GPIO.LOW)
        print("Lock OFF")
        time.sleep(5)  # Keep the lock OFF for 5 seconds

except KeyboardInterrupt:
    print("Exiting program.")
    GPIO.cleanup()  # Reset GPIO settings
