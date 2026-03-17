# wiggle_pins.py — drive two square waves for AND gate testing
#
# GPIO5 (RP_IO5) → wire to FPGA GPIO1 (PIN 14) = AND input 0
# GPIO6 (RP_IO6) → wire to FPGA GPIO2 (PIN 15) = AND input 1
#
# GPIO5 toggles at ~500 Hz, GPIO6 at ~250 Hz.
# FPGA GPIO0 (PIN 13) should show the AND of the two.
#
# Paste into RP2040 REPL.  Ctrl-C to stop.

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
