# gcd_test.py — automated UART GCD test with external reset
#
# Wiring:
#   RP2040 GPIO2  → FPGA GPIO3 (PIN 16) = ext_rst (PCB trace)
#   RP2040 GPIO8  → FPGA GPIO0 (PIN 13) = uart_rx (jumper)
#   RP2040 GPIO9  ← FPGA GPIO1 (PIN 14) = uart_tx (jumper)

from machine import UART, Pin
import math
import time

# Hold reset, init UART, then release
rst = Pin(2, Pin.OUT, value=1)
uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))
time.sleep_ms(100)
rst(0)
time.sleep_ms(100)

TIMEOUT_MS = 2000


def gcd_fpga(a, b):
    uart.read()  # flush
    uart.write(bytes([a & 0xFF]))
    uart.write(bytes([b & 0xFF]))
    start = time.ticks_ms()
    while not uart.any():
        if time.ticks_diff(time.ticks_ms(), start) > TIMEOUT_MS:
            return None
    return uart.read(1)[0]


test_cases = [
    (6, 4, 2),
    (48, 18, 6),
    (100, 75, 25),
    (7, 0, 7),
    (255, 255, 255),
]

print("UART GCD hardware test")
print("UART1 TX=GPIO8 RX=GPIO9, reset=GPIO2")
print()

ok = 0
for a, b, expected in test_cases:
    got = gcd_fpga(a, b)
    if got is None:
        status = "TIMEOUT"
    elif got == expected:
        status = "OK"
    else:
        status = f"FAIL (expected {expected})"
    if got == expected:
        ok += 1
    print(f"  gcd({a}, {b}) = {got} — {status}")

print(f"\n{ok}/{len(test_cases)} passed")
