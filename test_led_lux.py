import RPi.GPIO as GPIO
import time
import smbus  # For I2C communication with the lux sensor

# Set up GPIO mode for relay and LED control
GPIO.setmode(GPIO.BCM)
relay_pin = 17  # GPIO pin to control the relay
GPIO.setup(relay_pin, GPIO.OUT)

# Set up I2C communication for lux sensor (VEML7700 or other compatible sensor)
bus = smbus.SMBus(1)  # I2C bus (use 1 for Raspberry Pi)
sensor_address = 0x10  # Example I2C address of your lux sensor (adjust as needed)

# Function to read the lux value from the sensor
def read_lux():
    # Reading data from the sensor (assuming a specific I2C command, adjust as per your sensor's datasheet)
    lux_value = bus.read_word_data(sensor_address, 0x00)  # Read light level (change if needed)
    return lux_value

# Function to turn on the relay (LED on)
def turn_on_led():
    GPIO.output(relay_pin, GPIO.HIGH)  # This will close the relay and power the LED

# Function to turn off the relay (LED off)
def turn_off_led():
    GPIO.output(relay_pin, GPIO.LOW)  # This will open the relay and turn off the LED

# Set a lux threshold to turn the LED on (adjust based on your environment)
lux_threshold = 100  # Adjust this value based on your desired light threshold

# Main loop
try:
    while True:
        # Read the lux sensor value
        lux = read_lux()
        print(f"Lux Value: {lux}")  # Print lux value for debugging
        
        # Check if the lux value exceeds the threshold
        if lux > lux_threshold:
            turn_on_led()  # Turn on the LED
            print("LED On - Light level is high")
        else:
            turn_off_led()  # Turn off the LED
            print("LED Off - Light level is low")

        time.sleep(1)  # Wait 1 second before reading the sensor again

except KeyboardInterrupt:
    print("Program exited")

finally:
    GPIO.cleanup()  # Clean up GPIO before exiting
