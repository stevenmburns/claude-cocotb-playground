# gcd_client.py — MicroPython SPI GCD client for Vicharak Shrike RP2040
#
# 24-bit GCD over SPI Mode 0, MSB-first, 8-bit frames.
#
# Hardware connections (jumper wires unless noted):
#   RP2040 GPIO2  → FPGA GPIO3  (FPGA_IO3)  = ext_rst   (PCB trace)
#   RP2040 GPIO8  ← FPGA GPIO0  (FPGA_IO0)  = MISO      (SPI1_RX)
#   RP2040 GPIO9  → FPGA GPIO1  (FPGA_IO1)  = SS_N      (SPI1_CSn)
#   RP2040 GPIO10 → FPGA GPIO2  (FPGA_IO2)  = SCK       (SPI1_SCK)
#   RP2040 GPIO11 → FPGA GPIO7  (FPGA_IO7)  = MOSI      (SPI1_TX)
#   RP2040 GPIO5  ← FPGA GPIO17 (FPGA_IO17) = result_ready (IRQ)
#
# Protocol (matches spi_gcd_top.v):
#   3 transactions: a[7:0], a[15:8], a[23:16]  (LSB first)
#   3 transactions: b[7:0], b[15:8], b[23:16]  (LSB first)
#   Wait for result_ready
#   3 transactions: dummy → r[7:0], r[15:8], r[23:16]  (LSB first)

from machine import SPI, Pin
import asyncio

# Hardware SPI1: SCK=GPIO10, MOSI=GPIO11, MISO=GPIO8
spi = SPI(1, baudrate=1_000_000, polarity=0, phase=0,
          sck=Pin(10), mosi=Pin(11), miso=Pin(8))

# SS_N: GPIO9, active low, idle high
ss_n = Pin(9, Pin.OUT, value=1)

# External reset: GPIO2, active high
ext_rst = Pin(2, Pin.OUT, value=0)

# Result ready: GPIO5, input with IRQ
result_ready = Pin(5, Pin.IN)

# Async flag for result_ready IRQ
result_flag = asyncio.ThreadSafeFlag()
result_ready.irq(trigger=Pin.IRQ_RISING, handler=lambda _: result_flag.set())


def _transaction(byte_out: int) -> int:
    """Assert SS_N, transfer one byte, deassert SS_N; return received byte."""
    buf = bytearray([byte_out & 0xFF])
    ss_n(0)
    spi.write_readinto(buf, buf)
    ss_n(1)
    return buf[0]


def _send_24bit(value: int):
    """Send a 24-bit value as 3 SPI transactions, LSB first."""
    _transaction(value & 0xFF)
    _transaction((value >> 8) & 0xFF)
    _transaction((value >> 16) & 0xFF)


def _recv_24bit() -> int:
    """Receive a 24-bit value as 3 SPI transactions (dummy MOSI), LSB first."""
    b0 = _transaction(0x00)
    b1 = _transaction(0x00)
    b2 = _transaction(0x00)
    return b0 | (b1 << 8) | (b2 << 16)


def reset_fpga():
    """Pulse ext_rst high for ~10 ms to reset the FPGA FSM."""
    ext_rst(1)
    import time
    time.sleep_ms(10)
    ext_rst(0)
    time.sleep_ms(1)


async def gcd(a: int, b: int) -> int:
    """Send a, b to the FPGA over SPI and return the 24-bit GCD result."""
    _send_24bit(a)
    _send_24bit(b)
    # Wait for result_ready IRQ (or poll as fallback)
    try:
        await asyncio.wait_for_ms(result_flag.wait(), 1000)
    except asyncio.TimeoutError:
        if not result_ready():
            raise RuntimeError(f"Timeout waiting for result_ready (a={a}, b={b})")
    return _recv_24bit()


def gcd_sync(a: int, b: int) -> int:
    """Synchronous version: poll result_ready instead of using IRQ."""
    import time
    _send_24bit(a)
    _send_24bit(b)
    for _ in range(1000):
        if result_ready():
            break
        time.sleep_ms(1)
    else:
        raise RuntimeError(f"Timeout waiting for result_ready (a={a}, b={b})")
    return _recv_24bit()


def main():
    print("SPI GCD client — Vicharak Shrike (24-bit)")
    print("SPI1 SCK=GPIO10 MOSI=GPIO11 MISO=GPIO8 SS_N=GPIO9 @ 1 MHz")
    print("ext_rst=GPIO2 result_ready=GPIO5")
    print("Enter two integers 0–16777215. Ctrl-C to exit.\n")

    reset_fpga()

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

        if not (0 <= a <= 0xFFFFFF and 0 <= b <= 0xFFFFFF):
            print("  Values must be in range 0–16777215")
            continue

        result = gcd_sync(a, b)
        print(f"  gcd({a}, {b}) = {result}")


main()
