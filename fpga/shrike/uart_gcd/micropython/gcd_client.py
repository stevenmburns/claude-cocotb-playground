# gcd_client.py — MicroPython UART GCD client for Vicharak Shrike RP2040
#
# Hardware connections (internal PCB traces, no wires needed):
#   RP2040 GPIO0 (UART0 TX) → FPGA PIN 6 (GPIO15) = uart_rx on FPGA
#   RP2040 GPIO1 (UART0 RX) ← FPGA PIN 4 (GPIO13) = uart_tx on FPGA
#
# Protocol (matches gcd_top.v):
#   Host → FPGA : byte a  (0–255)
#   Host → FPGA : byte b  (0–255)
#   FPGA → Host : byte result = gcd(a, b)
#
# Copy this file to the RP2040 as main.py (or run interactively via REPL).

from machine import UART, Pin
import time

# UART0: TX=GPIO0, RX=GPIO1, 115200 8N1 — matches CLKS_PER_BIT=434 in gcd_top.v
uart = UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))

TIMEOUT_MS = 2000  # max wait for FPGA response


def gcd(a: int, b: int) -> int | None:
    """Send a, b to the FPGA and return the GCD result, or None on timeout."""
    uart.write(bytes([a & 0xFF, b & 0xFF]))
    deadline = time.ticks_add(time.ticks_ms(), TIMEOUT_MS)
    while not uart.any():
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            return None
    return uart.read(1)[0]


def main():
    print("UART GCD client — Vicharak Shrike")
    print(f"UART0 TX=GPIO0 RX=GPIO1 @ 115200 baud  timeout={TIMEOUT_MS}ms")
    print("Enter two integers 0–255. Ctrl-C to exit.\n")

    while True:
        try:
            a = int(input("a: "))
            b = int(input("b: "))
        except ValueError:
            print("  Enter integers 0–255")
            continue
        except KeyboardInterrupt:
            print("\nBye.")
            break

        if not (0 <= a <= 255 and 0 <= b <= 255):
            print("  Values must be in range 0–255")
            continue

        result = gcd(a, b)
        if result is None:
            print(f"  TIMEOUT — no response from FPGA after {TIMEOUT_MS} ms")
        else:
            print(f"  gcd({a}, {b}) = {result}")


main()

