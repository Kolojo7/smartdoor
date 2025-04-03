import board
import neopixel

NUM_PIXELS = 241
PIN = board.D18  # GPIO18 (PWM capable)

pixels = neopixel.NeoPixel(PIN, NUM_PIXELS, brightness=0.5, auto_write=True)

pixels.fill((255, 0, 0))  # Set all LEDs to red
