# gcd_client.py — MicroPython 24-bit SPI GCD client for Vicharak Shrike RP2040
#
# Wiring (board pin names):
#   Via PCB traces (no wires):
#     RP_IO0  → FPGA (internal) = ext_rst
#     RP_IO1  ← FPGA (internal) = result_ready
#   Via jumper wires:
#     RP_IO10 → FPGA_IO0 = spi_sck
#     RP_IO11 → FPGA_IO1 = spi_mosi
#     RP_IO8  ← FPGA_IO2 = spi_miso
#     RP_IO9  → FPGA_IO7 = spi_ss_n  (active low)
#
# Uses hardware SPI1: SCK=GPIO10, MOSI=GPIO11, MISO=GPIO8, CSn=GPIO9 (manual).
#
# Protocol (matches spi_gcd_top.v, SPI Mode 0, MSB-first bits, LSB-first bytes):
#   Transaction 1 (6 bytes, SS_N held low):
#     a[7:0], a[15:8], a[23:16], b[7:0], b[15:8], b[23:16]
#   Wait for result_ready to go high
#   Transaction 2 (3 bytes, SS_N held low):
#     MOSI ignored; MISO = r[7:0], r[15:8], r[23:16]
#
# Copy this file to the RP2040 as main.py (or run interactively via REPL).

from machine import SPI, Pin
import time

# External reset: hold high during init, release after peripherals ready
rst = Pin(0, Pin.OUT, value=1)

# Hardware SPI1: SCK=RP_IO10, MOSI=RP_IO11, MISO=RP_IO8
spi = SPI(
    1, baudrate=1_000_000, polarity=0, phase=0, sck=Pin(10), mosi=Pin(11), miso=Pin(8)
)

# SS_N: RP_IO9 → FPGA_IO7, active low; idle high (manual control)
ss_n = Pin(9, Pin.OUT, value=1)

# result_ready: RP_IO1 ← FPGA (PCB trace)
result_ready = Pin(1, Pin.IN)

# Release reset
time.sleep_ms(100)
rst(0)
time.sleep_ms(100)

TIMEOUT_MS = 1000


def to_bytes3(val):
    return bytes([val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF])


def from_bytes3(b):
    return b[0] | (b[1] << 8) | (b[2] << 16)


def gcd(a, b):
    """Send a, b (24-bit) to the FPGA over SPI and return the GCD result."""
    # Transaction 1: 6 bytes (a[2:0] + b[2:0]), SS_N held low
    tx = to_bytes3(a) + to_bytes3(b)
    ss_n(0)
    spi.write(tx)
    ss_n(1)

    # Wait for result_ready
    t0 = time.ticks_ms()
    while not result_ready():
        if time.ticks_diff(time.ticks_ms(), t0) > TIMEOUT_MS:
            raise TimeoutError("result_ready never asserted")

    # Transaction 2: 3 dummy bytes out, read result on MISO
    rx = bytearray(3)
    ss_n(0)
    spi.write_readinto(bytearray(3), rx)
    ss_n(1)

    return from_bytes3(rx)


def main():
    print("24-bit SPI GCD client — Vicharak Shrike")
    print("SPI1 SCK=RP_IO10 MOSI=RP_IO11 MISO=RP_IO8 SS_N=RP_IO9")
    print("ext_rst=RP_IO0 result_ready=RP_IO1 (PCB traces)")
    print("Enter two integers 0–16777215. Ctrl-C to exit.\n")

    while True:
        try:
            a = int(input("a: "))
            b = int(input("b: "))
        except ValueError:
            print("  Enter integers 0–16777215")
            continue
        except KeyboardInterrupt:
            print("\nBye.")
            break

        if not (0 <= a <= 16777215 and 0 <= b <= 16777215):
            print("  Values must be in range 0–16777215")
            continue

        result = gcd(a, b)
        print(f"  gcd({a}, {b}) = {result}")


main()
