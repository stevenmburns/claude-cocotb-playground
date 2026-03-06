import os
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge


async def reset(dut):
    dut.rst.value = 1
    dut.start.value = 0
    dut.a.value = 0
    dut.b.value = 0
    for _ in range(4):
        await RisingEdge(dut.clk)
    dut.rst.value = 0


async def compute_gcd(dut, a, b):
    dut.a.value = a
    dut.b.value = b
    dut.start.value = 1
    await RisingEdge(dut.clk)
    dut.start.value = 0

    for _ in range(200):
        await RisingEdge(dut.clk)
        if dut.done.value == 1:
            return int(dut.result.value)

    raise TimeoutError(f"GCD({a}, {b}) did not complete within 200 cycles")


@cocotb.test()
async def test_gcd(dut):
    a = int(os.environ["GCD_A"])
    b = int(os.environ["GCD_B"])
    expected = int(os.environ["GCD_EXPECTED"])

    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)
    result = await compute_gcd(dut, a, b)
    assert result == expected, f"GCD({a}, {b}): expected {expected}, got {result}"
