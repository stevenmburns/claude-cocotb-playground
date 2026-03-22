# gcd_test.py — automated 24-bit UART GCD test with external reset
#
# Protocol: 3 bytes a (LSB first) + 3 bytes b (LSB first) → 3 bytes result
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

TIMEOUT_MS = 5000


def to_bytes3(val):
    return bytes([val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF])


def from_bytes3(b):
    return b[0] | (b[1] << 8) | (b[2] << 16)


def gcd_fpga(a, b):
    uart.read()  # flush
    uart.write(to_bytes3(a))
    uart.write(to_bytes3(b))
    start = time.ticks_ms()
    buf = b""
    while len(buf) < 3:
        if time.ticks_diff(time.ticks_ms(), start) > TIMEOUT_MS:
            return None
        chunk = uart.read(3 - len(buf))
        if chunk:
            buf += chunk
        time.sleep_ms(1)
    return from_bytes3(buf)


test_cases = [
    (6, 4, 2),
    (48, 18, 6),
    (100, 75, 25),
    (255, 255, 255),
    (1000000, 750000, 250000),
    (16777215, 16777215, 16777215),  # max 24-bit
    (123456, 7890, 6),
    (0, 42, 42),
]

print("24-bit UART GCD hardware test")
print("UART1 TX=GPIO8 RX=GPIO9, reset=GPIO2")
print()

ok = 0
for a, b, expected in test_cases:
    got = gcd_fpga(a, b)
    if got is None:
        status = "TIMEOUT"
    elif got == expected:
        status = "OK"
        ok += 1
    else:
        status = "FAIL (expected {})".format(expected)
    print("  gcd({}, {}) = {} — {}".format(a, b, got, status))

print("\n{}/{} passed".format(ok, len(test_cases)))
