import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CLK_PERIOD_NS = 10
CLKS_PER_BIT = 8  # matched to build arg -GCLKS_PER_BIT=8


async def uart_send_byte(dut, byte_val, cpb):
    """Drive dut.uart_rx with one 8N1 byte (LSB first)."""
    # start bit
    dut.uart_rx.value = 0
    for _ in range(cpb):
        await RisingEdge(dut.clk)
    # 8 data bits, LSB first
    for i in range(8):
        dut.uart_rx.value = (byte_val >> i) & 1
        for _ in range(cpb):
            await RisingEdge(dut.clk)
    # stop bit
    dut.uart_rx.value = 1
    for _ in range(cpb):
        await RisingEdge(dut.clk)


async def uart_recv_byte(dut, cpb):
    """Sample dut.uart_tx to receive one 8N1 byte."""
    # wait for start bit (falling edge)
    while dut.uart_tx.value != 0:
        await RisingEdge(dut.clk)
    # skip to centre of first data bit: 1.5 bit periods from start edge
    for _ in range(cpb + cpb // 2):
        await RisingEdge(dut.clk)
    # sample 8 bits
    byte_val = 0
    for i in range(8):
        byte_val |= int(dut.uart_tx.value) << i
        if i < 7:
            for _ in range(cpb):
                await RisingEdge(dut.clk)
    # wait through remainder of bit 7 and the full stop bit
    for _ in range(cpb // 2 + cpb):
        await RisingEdge(dut.clk)
    return byte_val


def to_bytes3(val):
    """Convert a 24-bit integer to 3 bytes (LSB first)."""
    return [val & 0xFF, (val >> 8) & 0xFF, (val >> 16) & 0xFF]


def from_bytes3(b):
    """Convert 3 bytes (LSB first) to a 24-bit integer."""
    return b[0] | (b[1] << 8) | (b[2] << 16)


@cocotb.test()
async def test_gcd_uart(dut):
    a = int(os.environ["GCD_A"])
    b = int(os.environ["GCD_B"])
    expected = int(os.environ["GCD_EXPECTED"])
    cpb = CLKS_PER_BIT

    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
    dut.uart_rx.value = 1  # idle high

    # Assert external reset for 16 cycles, then release
    dut.ext_rst.value = 1
    for _ in range(16):
        await RisingEdge(dut.clk)
    dut.ext_rst.value = 0
    # Wait for reset synchroniser to propagate (2 FF stages + margin)
    for _ in range(8):
        await RisingEdge(dut.clk)

    # Send 3 bytes for a, then 3 bytes for b (LSB first)
    for byte_val in to_bytes3(a):
        await uart_send_byte(dut, byte_val, cpb)
    for byte_val in to_bytes3(b):
        await uart_send_byte(dut, byte_val, cpb)

    # Receive 3 result bytes (LSB first)
    result_bytes = []
    for _ in range(3):
        result_bytes.append(await uart_recv_byte(dut, cpb))
    result = from_bytes3(result_bytes)
    assert result == expected, f"GCD({a},{b}): expected {expected}, got {result}"
