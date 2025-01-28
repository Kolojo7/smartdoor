import time
import board
import busio
from adafruit_veml7700 import VEML7700

# Initialize the I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize the VEML7700 sensor
veml7700 = VEML7700(i2c)

# Adjust sensor settings
veml7700.light_gain = 1  # Default is 1
veml7700.integration_time = 100  # Default is 100ms

# Output light readings in a loop
try:
    while True:
        print(f"Ambient Light Level: {veml7700.lux:.2f} lux")
        time.sleep(1)  # Wait 1 second between readings
except KeyboardInterrupt:
    print("Exiting program.")

