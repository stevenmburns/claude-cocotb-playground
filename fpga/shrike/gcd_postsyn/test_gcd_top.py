"""Gate-level UART testbench for gcd_top post-synthesis netlist.

CLKS_PER_BIT is 5208 (50 MHz / 9600 baud), matching what Yosys baked into
the netlist.  The test sends two bytes over uart_rx, then samples the result
byte from uart_tx and asserts it equals gcd(a, b).
"""

import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CLK_PERIOD_NS = 20  # 50 MHz
CLKS_PER_BIT = 5208  # baked into netlist: 50_000_000 / 9600


async def uart_send_byte(dut, byte_val, cpb):
    """Drive dut.uart_rx with one 8N1 byte (LSB first)."""
    dut.uart_rx.value = 0  # start bit
    for _ in range(cpb):
        await RisingEdge(dut.clk)
    for i in range(8):
        dut.uart_rx.value = (byte_val >> i) & 1
        for _ in range(cpb):
            await RisingEdge(dut.clk)
    dut.uart_rx.value = 1  # stop bit
    for _ in range(cpb):
        await RisingEdge(dut.clk)


async def uart_recv_byte(dut, cpb):
    """Sample dut.uart_tx to receive one 8N1 byte."""
    # wait for start bit (falling edge)
    while dut.uart_tx.value != 0:
        await RisingEdge(dut.clk)
    # advance to centre of first data bit: 1.5 bit-periods from start edge
    for _ in range(cpb + cpb // 2):
        await RisingEdge(dut.clk)
    byte_val = 0
    for i in range(8):
        byte_val |= int(dut.uart_tx.value) << i
        if i < 7:
            for _ in range(cpb):
                await RisingEdge(dut.clk)
    # consume remainder of bit 7 and the stop bit
    for _ in range(cpb // 2 + cpb):
        await RisingEdge(dut.clk)
    return byte_val


@cocotb.test()
async def test_gcd_uart(dut):
    a = int(os.environ["GCD_A"])
    b = int(os.environ["GCD_B"])
    expected = int(os.environ["GCD_EXPECTED"])
    cpb = CLKS_PER_BIT

    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())
    dut.uart_rx.value = 1  # idle high

    # Wait for internal power-on reset to clear (~16 cycles)
    for _ in range(32):
        await RisingEdge(dut.clk)

    await uart_send_byte(dut, a, cpb)
    await uart_send_byte(dut, b, cpb)
    result = await uart_recv_byte(dut, cpb)

    assert result == expected, f"GCD({a},{b}): expected {expected}, got {result}"
