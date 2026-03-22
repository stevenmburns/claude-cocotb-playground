# spi_test.py — automated 8-bit SPI GCD test with external reset + asyncio IRQ
#
# Wiring (board pin names):
#   RP_IO0  → FPGA (internal) = ext_rst        (PCB trace)
#   RP_IO1  ← FPGA (internal) = result_ready   (PCB trace)
#   RP_IO10 → FPGA_IO0        = spi_sck        (jumper wire)
#   RP_IO11 → FPGA_IO1        = spi_mosi       (jumper wire)
#   RP_IO8  ← FPGA_IO2        = spi_miso       (jumper wire)
#   RP_IO9  → FPGA_IO7        = spi_ss_n       (jumper wire)
#
# Uses hardware SPI1 and asyncio.ThreadSafeFlag for interrupt-driven wait.

import asyncio
from machine import SPI, Pin
import time

TIMEOUT_S = 10  # seconds

# External reset: hold high, init peripherals, then release
rst = Pin(0, Pin.OUT, value=1)

# Hardware SPI1: SCK=RP_IO10, MOSI=RP_IO11, MISO=RP_IO8
spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(10), mosi=Pin(11), miso=Pin(8))

# SS_N: RP_IO9 → FPGA_IO7, active low; idle high (manual control)
ss_n = Pin(9, Pin.OUT, value=1)

# result_ready IRQ → ThreadSafeFlag (safe to set from ISR, await from coroutine)
_result_flag = asyncio.ThreadSafeFlag()
result_pin = Pin(1, Pin.IN)
result_pin.irq(trigger=Pin.IRQ_RISING, handler=lambda p: _result_flag.set())

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


async def gcd_fpga(a, b):
    """Send a, b over SPI; await IRQ for result_ready; read result."""
    _transaction(a)  # transaction 1: load a
    _transaction(b)  # transaction 2: load b; GCD starts after SS_N deasserts

    # Await result_ready rising edge — no polling, CPU can sleep
    try:
        await asyncio.wait_for(_result_flag.wait(), TIMEOUT_S)
    except asyncio.TimeoutError:
        return None

    return _transaction(0x00)  # transaction 3: clock out result


test_cases = [
    (12, 8, 4),
    (48, 18, 6),
    (0, 5, 5),
    (7, 0, 7),
    (1, 1, 1),
    (255, 170, 85),
]


async def main():
    print("8-bit SPI GCD hardware test (asyncio)")
    print("SPI1 SCK=RP_IO10 MOSI=RP_IO11 MISO=RP_IO8 SS_N=RP_IO9")
    print("ext_rst=RP_IO0 result_ready=RP_IO1 (PCB traces)")
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
