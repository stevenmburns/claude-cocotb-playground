import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CLK_PERIOD_NS = 20  # 50 MHz
SPI_SCK_HALF = 4  # clocks per SCK half-period (> 2-cycle sync latency)
RESULT_READY_MAX_CYCLES = 50000  # enough for worst-case 24-bit binary GCD


async def spi_transaction(dut, byte_out):
    """Bit-bang one 8-bit SPI Mode 0 transaction (MSB first). Returns received byte."""
    rx_byte = 0

    # Assert SS_N (active low); wait for sync margin
    dut.spi_ss_n.value = 0
    for _ in range(SPI_SCK_HALF):
        await RisingEdge(dut.clk)

    for i in range(7, -1, -1):  # MSB first
        # SCK low: set MOSI
        dut.spi_sck.value = 0
        dut.spi_mosi.value = (byte_out >> i) & 1
        for _ in range(SPI_SCK_HALF):
            await RisingEdge(dut.clk)

        # SCK high: target samples MOSI; wait full half-period then sample MISO
        dut.spi_sck.value = 1
        for _ in range(SPI_SCK_HALF):
            await RisingEdge(dut.clk)
        rx_bit = int(dut.spi_miso.value)
        rx_byte = (rx_byte << 1) | rx_bit

    # Final SCK low, then deassert SS_N
    dut.spi_sck.value = 0
    for _ in range(SPI_SCK_HALF):
        await RisingEdge(dut.clk)
    dut.spi_ss_n.value = 1
    for _ in range(SPI_SCK_HALF):
        await RisingEdge(dut.clk)

    return rx_byte


async def spi_send_24bit(dut, value):
    """Send a 24-bit value as 3 SPI transactions, LSB first."""
    await spi_transaction(dut, value & 0xFF)
    await spi_transaction(dut, (value >> 8) & 0xFF)
    await spi_transaction(dut, (value >> 16) & 0xFF)


async def spi_recv_24bit(dut):
    """Receive a 24-bit value as 3 SPI transactions (dummy MOSI), LSB first."""
    b0 = await spi_transaction(dut, 0x00)
    b1 = await spi_transaction(dut, 0x00)
    b2 = await spi_transaction(dut, 0x00)
    return b0 | (b1 << 8) | (b2 << 16)


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

    # Send a (3 bytes, LSB first)
    await spi_send_24bit(dut, a)
    # Send b (3 bytes, LSB first)
    await spi_send_24bit(dut, b)

    # Poll result_ready (level-sensitive)
    for _ in range(RESULT_READY_MAX_CYCLES):
        if dut.result_ready.value:
            break
        await RisingEdge(dut.clk)
    else:
        assert False, f"Timeout: result_ready never asserted for GCD({a},{b})"

    # Read result (3 bytes, LSB first)
    result = await spi_recv_24bit(dut)

    assert result == expected, f"GCD({a},{b}): expected {expected}, got {result}"
