import math
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
    """Drive inputs, wait for done, return result."""
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
async def test_basic(dut):
    """Simple known-value checks."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)

    cases = [
        (48, 18, 6),
        (100, 75, 25),
        (1, 1, 1),
        (7, 0, 7),
        (0, 5, 5),
    ]

    for a, b, expected in cases:
        result = await compute_gcd(dut, a, b)
        assert result == expected, f"GCD({a},{b}): expected {expected}, got {result}"
        dut._log.info(f"GCD({a}, {b}) = {result}  OK")
        await reset(dut)


@cocotb.test()
async def test_large(dut):
    """64-bit inputs compared against Python math.gcd."""
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())
    await reset(dut)

    cases = [
        (2**32, 2**16),
        (1_000_000_007, 998_244_353),
        (123_456_789_012_345, 987_654_321_098_765),
    ]

    for a, b in cases:
        expected = math.gcd(a, b)
        result = await compute_gcd(dut, a, b)
        assert result == expected, f"GCD({a},{b}): expected {expected}, got {result}"
        dut._log.info(f"GCD({a}, {b}) = {result}  OK")
        await reset(dut)
