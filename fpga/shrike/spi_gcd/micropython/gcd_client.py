# gcd_client.py — MicroPython SPI GCD client for Vicharak Shrike RP2040
#
# Wiring (board pin names):
#   Via PCB traces (no wires):
#     RP_IO0 → FPGA (internal) = ext_rst
#     RP_IO1 ← FPGA (internal) = result_ready
#   Via jumper wires:
#     RP_IO10 → FPGA_IO0 = spi_sck
#     RP_IO11 → FPGA_IO1 = spi_mosi
#     RP_IO8  ← FPGA_IO2 = spi_miso
#     RP_IO9  → FPGA_IO7 = spi_ss_n  (active low)
#
# Uses hardware SPI1: SCK=GPIO10, MOSI=GPIO11, MISO=GPIO8, CSn=GPIO9.
#
# Protocol (matches spi_gcd_top.v, SPI Mode 0 MSB-first):
#   Transaction 1: MOSI = a (0–255)       — FPGA stores a
#   Transaction 2: MOSI = b (0–255)       — FPGA stores b; GCD starts after SS_N deasserts
#   Wait for result_ready (RP_IO1) to go high
#   Transaction 3: MOSI = 0x00 (dummy)    — MISO = gcd(a, b)
#
# Copy this file to the RP2040 as main.py (or run interactively via REPL).

from machine import SPI, Pin
import time

# External reset: hold high during init, release after peripherals ready
rst = Pin(0, Pin.OUT, value=1)

# Hardware SPI1: SCK=RP_IO10, MOSI=RP_IO11, MISO=RP_IO8
spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(10), mosi=Pin(11), miso=Pin(8))

# SS_N: RP_IO9 → FPGA_IO7, active low; idle high (hardware CSn not used — manual control)
ss_n = Pin(9, Pin.OUT, value=1)

# result_ready: RP_IO1 ← FPGA (PCB trace)
result_ready = Pin(1, Pin.IN)

# Release reset
time.sleep_ms(100)
rst(0)
time.sleep_ms(100)

TIMEOUT_MS = 1000


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

    # Wait for result_ready
    t0 = time.ticks_ms()
    while not result_ready():
        if time.ticks_diff(time.ticks_ms(), t0) > TIMEOUT_MS:
            raise TimeoutError("result_ready never asserted")

    return _transaction(0x00)  # transaction 3: clock out result


def main():
    print("SPI GCD client — Vicharak Shrike")
    print("SPI1 SCK=RP_IO10 MOSI=RP_IO11 MISO=RP_IO8 SS_N=RP_IO9")
    print("ext_rst=RP_IO0 result_ready=RP_IO1 (PCB traces)")
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
