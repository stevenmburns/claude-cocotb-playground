# gcd_client.py — MicroPython I2C GCD client for Vicharak Shrike RP2040
#
# Hardware connections (internal PCB traces, no wires needed):
#   RP2040 GPIO0 (SoftI2C SCL) → FPGA PIN 6 (GPIO15) = i2c_scl on FPGA
#   RP2040 GPIO1 (SoftI2C SDA) ↔ FPGA PIN 4 (GPIO13) = i2c_sda on FPGA
#   FPGA PIN 5 (GPIO14)        = result_ready debug output (optional, logic analyser)
#
# Note: SoftI2C is used (not hardware I2C) because the RP2040 hardware I2C0
# assigns SDA to even-numbered GPIOs and SCL to odd-numbered GPIOs, which
# would swap the two lines relative to the physical board connections.
#
# Protocol (matches i2c_gcd_top.v, target address 0x08):
#   Master writes byte a  (0–255)
#   Master writes byte b  (0–255)
#   FPGA computes GCD (~microseconds at 50 MHz)
#   Master reads 1 byte   → result = gcd(a, b)
#
# Copy this file to the RP2040 as main.py (or run interactively via REPL).

from machine import SoftI2C, Pin
import time

# SoftI2C: SCL=GPIO0 → FPGA PIN 6 (i2c_scl), SDA=GPIO1 ↔ FPGA PIN 4 (i2c_sda)
i2c = SoftI2C(scl=Pin(0), sda=Pin(1), freq=100_000)

I2C_ADDR = 0x08  # matches I2C_TARGET_ADR in i2c_gcd_top.v
GCD_DELAY_MS = 2  # GCD finishes in microseconds; 2 ms is a safe margin


def gcd(a: int, b: int) -> int:
    """Send a, b to the FPGA over I2C and return the GCD result."""
    i2c.writeto(I2C_ADDR, bytes([a & 0xFF]))
    i2c.writeto(I2C_ADDR, bytes([b & 0xFF]))
    time.sleep_ms(GCD_DELAY_MS)
    return i2c.readfrom(I2C_ADDR, 1)[0]


def main():
    print("I2C GCD client — Vicharak Shrike")
    print(f"SoftI2C SCL=GPIO0 SDA=GPIO1 @ 100 kHz  addr=0x{I2C_ADDR:02X}")
    print("Enter two integers 0–255. Ctrl-C to exit.\n")

    # Scan for the target at startup
    found = i2c.scan()
    if I2C_ADDR not in found:
        print(
            f"WARNING: target 0x{I2C_ADDR:02X} not found on bus (scan={[hex(a) for a in found]})"
        )
        print("Check FPGA is programmed and power is on.\n")

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
        except OSError as e:
            print(f"  I2C error: {e}")


main()
