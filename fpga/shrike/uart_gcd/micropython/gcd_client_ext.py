# gcd_client_ext.py — UART GCD client using external jumper wires
#
# Wiring:
#   RP2040 GPIO8 (UART1 TX) → FPGA GPIO0 (PIN 13 / FPGA_IO0) = uart_rx
#   RP2040 GPIO9 (UART1 RX) ← FPGA GPIO1 (PIN 14 / FPGA_IO1) = uart_tx
#
# Uses hardware UART1 (not UART0) to avoid the internal SPI config pins.
# Probe FPGA_IO0 and FPGA_IO1 on the logic analyser to see traffic.

from machine import UART, Pin
import time

uart = UART(1, baudrate=115200, tx=Pin(8), rx=Pin(9))

TIMEOUT_MS = 2000


def gcd(a: int, b: int) -> int:
    uart.write(bytes([a & 0xFF]))
    uart.write(bytes([b & 0xFF]))
    start = time.ticks_ms()
    while not uart.any():
        if time.ticks_diff(time.ticks_ms(), start) > TIMEOUT_MS:
            raise TimeoutError(f"No response after {TIMEOUT_MS} ms")
    return uart.read(1)[0]


def main():
    print("UART GCD client (external jumper wires)")
    print("UART1 TX=GPIO8 RX=GPIO9 @ 115200")
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

        try:
            result = gcd(a, b)
            print(f"  gcd({a}, {b}) = {result}")
        except TimeoutError as e:
            print(f"  {e}")


main()
