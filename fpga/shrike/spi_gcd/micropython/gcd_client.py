# gcd_client.py — MicroPython SPI GCD client for Vicharak Shrike RP2040
#
# Hardware connections:
#   Via internal PCB traces (no wires):
#     RP2040 GPIO0 → FPGA PIN 6 (GPIO15) = spi_sck
#     RP2040 GPIO1 → FPGA PIN 4 (GPIO13) = spi_mosi
#   Via external jumper wires:
#     RP2040 GPIO2 ← FPGA PIN 5 (GPIO14) = spi_miso
#     RP2040 GPIO3 → FPGA PIN 3 (GPIO12) = spi_ss_n  (active low)
#
# Note: SoftSPI is used because the RP2040 hardware SPI0 assigns MISO to GPIO0
# and CSn to GPIO1 — both are fixed PCB traces used for SCK and MOSI here.
#
# Protocol (matches spi_gcd_top.v, SPI Mode 0 MSB-first):
#   Transaction 1: MOSI = a (0–255)       — FPGA stores a
#   Transaction 2: MOSI = b (0–255)       — FPGA stores b; GCD starts after SS_N deasserts
#   Delay ~1 ms    (GCD finishes in microseconds at 50 MHz)
#   Transaction 3: MOSI = 0x00 (dummy)    — MISO = gcd(a, b)
#
# Copy this file to the RP2040 as main.py (or run interactively via REPL).

from machine import SoftSPI, Pin
import time

# SoftSPI: SCK=GPIO0 (PCB), MOSI=GPIO1 (PCB), MISO=GPIO2 (jumper)
spi = SoftSPI(
    baudrate=1_000_000, polarity=0, phase=0, sck=Pin(0), mosi=Pin(1), miso=Pin(2)
)

# SS_N: GPIO3 → FPGA PIN 3 (GPIO12), active low; idle high
ss_n = Pin(3, Pin.OUT, value=1)

GCD_DELAY_MS = 2  # GCD finishes in microseconds; 2 ms is a safe margin


def _transaction(byte_out: int) -> int:
    """Assert SS_N, transfer one byte, deassert SS_N; return received byte."""
    buf = bytearray([byte_out & 0xFF])
    ss_n(0)
    spi.write_readinto(buf, buf)
    ss_n(1)
    return buf[0]


def gcd(a: int, b: int) -> int:
    """Send a, b to the FPGA over SPI and return the GCD result."""
    _transaction(a)  # transaction 1: load a
    _transaction(b)  # transaction 2: load b; GCD starts after SS_N deasserts
    time.sleep_ms(GCD_DELAY_MS)
    return _transaction(0x00)  # transaction 3: clock out result


def main():
    print("SPI GCD client — Vicharak Shrike")
    print("SoftSPI SCK=GPIO0 MOSI=GPIO1 MISO=GPIO2 SS_N=GPIO3 @ 1 MHz")
    print("FPGA pins: SCK=PIN6 MOSI=PIN4 MISO=PIN5(jumper) SS_N=PIN3(jumper)")
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
        print(f"  gcd({a}, {b}) = {result}")


main()
