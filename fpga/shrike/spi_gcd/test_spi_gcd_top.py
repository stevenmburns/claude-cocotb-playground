import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CLK_PERIOD_NS = 20  # 50 MHz
SPI_SCK_HALF = 4  # clocks per SCK half-period (> 2-cycle sync latency)
RESULT_READY_MAX_CYCLES = 5000  # enough for worst-case GCD(255,1)


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

    # Wait for internal power-on reset to clear (~16 cycles)
    for _ in range(32):
        await RisingEdge(dut.clk)

    await spi_transaction(dut, a)  # send a; MISO ignored
    await spi_transaction(dut, b)  # send b; MISO ignored; GCD starts

    # Poll result_ready (level-sensitive) — avoids missing the edge if GCD finishes
    # before we get here, while still bounding the VCD size with a cycle limit.
    for _ in range(RESULT_READY_MAX_CYCLES):
        if dut.result_ready.value:
            break
        await RisingEdge(dut.clk)
    else:
        assert False, f"Timeout: result_ready never asserted for GCD({a},{b})"

    result = await spi_transaction(dut, 0x00)  # dummy → captures GCD result on MISO

    assert result == expected, f"GCD({a},{b}): expected {expected}, got {result}"
