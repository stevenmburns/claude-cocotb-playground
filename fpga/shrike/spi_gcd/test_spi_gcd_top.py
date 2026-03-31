import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CLK_PERIOD_NS = 20  # 50 MHz
SPI_SCK_HALF = 4  # clocks per SCK half-period (> 2-cycle sync latency)
RESULT_READY_MAX_CYCLES = 50000  # enough for worst-case 24-bit binary GCD


async def spi_byte(dut, byte_out):
    """Bit-bang one 8-bit SPI Mode 0 byte (MSB first) within an active transaction.
    SS_N must already be asserted by the caller. Returns received byte."""
    rx_byte = 0

    for i in range(7, -1, -1):  # MSB first
        # SCK low: set MOSI
        dut.spi_sck.value = 0
        dut.spi_mosi.value = (byte_out >> i) & 1
        for _ in range(SPI_SCK_HALF):
            await RisingEdge(dut.clk)

        # SCK high: target samples MOSI; wait then sample MISO
        dut.spi_sck.value = 1
        for _ in range(SPI_SCK_HALF):
            await RisingEdge(dut.clk)
        rx_bit = int(dut.spi_miso.value)
        rx_byte = (rx_byte << 1) | rx_bit

    # Final SCK low
    dut.spi_sck.value = 0
    for _ in range(SPI_SCK_HALF):
        await RisingEdge(dut.clk)

    return rx_byte


async def spi_transaction(dut, tx_bytes):
    """Assert SS_N, transfer multiple bytes, deassert SS_N. Returns list of received bytes."""
    rx_bytes = []

    dut.spi_ss_n.value = 0
    for _ in range(SPI_SCK_HALF):
        await RisingEdge(dut.clk)

    for b in tx_bytes:
        rx = await spi_byte(dut, b)
        rx_bytes.append(rx)

    dut.spi_ss_n.value = 1
    for _ in range(SPI_SCK_HALF):
        await RisingEdge(dut.clk)

    return rx_bytes


def to_bytes3(val):
    """Convert 24-bit integer to 3 bytes, LSB first."""
    return bytes([val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF])


def from_bytes3(b):
    """Convert 3 bytes (LSB first) to 24-bit integer."""
    return b[0] | (b[1] << 8) | (b[2] << 16)


@cocotb.test()
async def test_gcd_spi(dut):
    a = int(os.environ["GCD_A"])
    b = int(os.environ["GCD_B"])
    expected = int(os.environ["GCD_EXPECTED"])

    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    # Idle state
    dut.spi_ss_n.value = 1
    dut.spi_sck.value = 0
    dut.spi_mosi.value = 0

    # Assert external reset for a few cycles, then release
    dut.ext_rst.value = 1
    for _ in range(8):
        await RisingEdge(dut.clk)
    dut.ext_rst.value = 0
    for _ in range(4):
        await RisingEdge(dut.clk)

    # Send a (3 bytes, LSB first) — one byte per SS_N assertion
    await spi_transaction(dut, [to_bytes3(a)[0]])
    await spi_transaction(dut, [to_bytes3(a)[1]])
    await spi_transaction(dut, [to_bytes3(a)[2]])
    # Send b (3 bytes, LSB first)
    await spi_transaction(dut, [to_bytes3(b)[0]])
    await spi_transaction(dut, [to_bytes3(b)[1]])
    await spi_transaction(dut, [to_bytes3(b)[2]])

    # Poll result_ready (level-sensitive)
    for _ in range(RESULT_READY_MAX_CYCLES):
        if dut.result_ready.value:
            break
        await RisingEdge(dut.clk)
    else:
        assert False, f"Timeout: result_ready never asserted for GCD({a},{b})"

    # Read result (3 bytes, LSB first)
    rx = await spi_transaction(dut, [0x00, 0x00, 0x00])
    result = from_bytes3(rx)

    assert result == expected, f"GCD({a},{b}): expected {expected}, got {result}"
