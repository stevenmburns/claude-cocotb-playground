# enable_toggle.py — toggle the FPGA counter enable at ~1 kHz
#
# RP2040 GPIO2 → FPGA PIN 16 (GPIO3) via PCB trace (per Vicharak examples)
# Counter runs when enable is high, freezes when low.
#
# Note: GPIO0–3 are SPI config pins and cannot be driven as GPIO
# outputs without disrupting FPGA operation.
#
# On the logic analyser you should see the 100/50 KHz counter outputs
# gated by a 1 kHz envelope.
#
# Paste into RP2040 REPL.  Ctrl-C to stop.

from machine import Pin
import time

enable = Pin(2, Pin.OUT)

print("Toggling enable (RP2040 GPIO2 → FPGA PIN 16/GPIO3) at ~1 kHz")
print("Ctrl-C to stop.")

try:
    while True:
        enable.toggle()
        time.sleep_us(500)  # 500 us half-period → 1 kHz
except KeyboardInterrupt:
    enable(0)
    print("\nStopped — enable driven low.")
