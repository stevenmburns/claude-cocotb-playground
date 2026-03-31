# spi_test.py — automated 24-bit SPI GCD test with external reset + IRQ
#
# Protocol: 3 × 1-byte SPI transactions for a (LSB first)
#           3 × 1-byte SPI transactions for b (LSB first)
#           await result_ready via ThreadSafeFlag
#           3 × 1-byte SPI transactions → result (LSB first)
#
# Wiring (jumper wires unless noted):
#   RP2040 GPIO2  → FPGA GPIO3  (FPGA_IO3)  = ext_rst      (PCB trace)
#   RP2040 GPIO8  ← FPGA GPIO0  (FPGA_IO0)  = MISO         (SPI1_RX)
#   RP2040 GPIO9  → FPGA GPIO1  (FPGA_IO1)  = SS_N         (SPI1_CSn)
#   RP2040 GPIO10 → FPGA GPIO2  (FPGA_IO2)  = SCK          (SPI1_SCK)
#   RP2040 GPIO11 → FPGA GPIO7  (FPGA_IO7)  = MOSI         (SPI1_TX)
#   RP2040 GPIO5  ← FPGA GPIO17 (FPGA_IO17) = result_ready (IRQ)

import asyncio
from machine import SPI, Pin
import time

# External reset: hold high, init peripherals, then release
rst = Pin(2, Pin.OUT, value=1)

# Hardware SPI1: SCK=GPIO10, MOSI=GPIO11, MISO=GPIO8
# Do NOT pass cs= — we manage SS_N manually for 1-byte transactions
spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(10), mosi=Pin(11), miso=Pin(8))

# SS_N: GPIO9, active low, idle high (manual control for 1-byte transactions)
ss_n = Pin(9, Pin.OUT, value=1)

# result_ready IRQ → ThreadSafeFlag
_result_flag = asyncio.ThreadSafeFlag()
result_pin = Pin(5, Pin.IN)
result_pin.irq(trigger=Pin.IRQ_RISING, handler=lambda p: _result_flag.set())

TIMEOUT_S = 10

# Release reset
time.sleep_ms(100)
rst(0)
time.sleep_ms(100)


def _transaction(byte_out):
    """Assert SS_N, transfer one byte, deassert SS_N; return received byte."""
    buf = bytearray([byte_out & 0xFF])
    ss_n(0)
    spi.write_readinto(buf, buf)
    ss_n(1)
    return buf[0]


def to_bytes3(val):
    return [val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF]


def from_bytes3(b):
    return b[0] | (b[1] << 8) | (b[2] << 16)


async def gcd_fpga(a, b):
    """Send a, b (24-bit, 3 bytes each LSB first) over SPI; await IRQ; read 3-byte result."""
    for byte in to_bytes3(a):
        _transaction(byte)
    for byte in to_bytes3(b):
        _transaction(byte)

    # Await result_ready rising edge
    try:
        await asyncio.wait_for(_result_flag.wait(), TIMEOUT_S)
    except asyncio.TimeoutError:
        return None

    # Read 3 bytes (dummy MOSI, capture MISO)
    result_bytes = [_transaction(0x00) for _ in range(3)]
    return from_bytes3(result_bytes)


test_cases = [
    (12, 8, 4),
    (48, 18, 6),
    (0, 5, 5),
    (7, 0, 7),
    (1, 1, 1),
    (255, 170, 85),
    (1000000, 750000, 250000),
    (123456, 7890, 6),
    (16777215, 16777215, 16777215),  # max 24-bit
    (16777215, 1, 1),                # worst case
]


async def main():
    print("24-bit SPI GCD hardware test (asyncio)")
    print("SPI1 SCK=GPIO10 MOSI=GPIO11 MISO=GPIO8 SS_N=GPIO9 @ 1 MHz")
    print("ext_rst=GPIO2, result_ready=GPIO5")
    print()

    ok = 0
    for a, b, expected in test_cases:
        t0 = time.ticks_ms()
        got = await gcd_fpga(a, b)
        elapsed = time.ticks_diff(time.ticks_ms(), t0)
        if got is None:
            status = "TIMEOUT"
        elif got == expected:
            status = "OK"
            ok += 1
        else:
            status = "FAIL (expected {})".format(expected)
        print("  gcd({}, {}) = {} — {} ({}ms)".format(a, b, got, status, elapsed))

    print("\n{}/{} passed".format(ok, len(test_cases)))


asyncio.run(main())
