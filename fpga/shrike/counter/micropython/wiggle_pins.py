# wiggle_pins.py — MicroPython pin wiggler for logic analyser debugging
#
# Toggles RP2040 GPIO5 and GPIO6 in an alternating pattern so you can
# verify the logic analyser is capturing signals on RP_IO5 / RP_IO6.
#
# Hardware (Vicharak Shrike):
#   RP_IO5 = RP2040 GPIO5 (I2C0_SCL / UART1_RX / SPI0_CSn) — toggles at ~500 Hz
#   RP_IO6 = RP2040 GPIO6                                    — toggles at ~250 Hz
#
# Copy to RP2040 as main.py or paste into REPL.  Ctrl-C to stop.

from machine import Pin
import time

p0 = Pin(5, Pin.OUT)
p1 = Pin(6, Pin.OUT)

print("Wiggling RP_IO5/GPIO5 (~500 Hz) and RP_IO6/GPIO6 (~250 Hz)")
print("Ctrl-C to stop.")

count = 0
try:
    while True:
        p0.toggle()
        if count % 2 == 0:
            p1.toggle()
        count += 1
        time.sleep_ms(1)
except KeyboardInterrupt:
    p0(0)
    p1(0)
    print("\nStopped — pins driven low.")
