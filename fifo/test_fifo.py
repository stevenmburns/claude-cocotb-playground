import cocotb
import random
from collections import deque
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ReadOnly


@cocotb.test()
async def test_random_traffic(dut):
    """Random valid/ready each cycle; deque reference model verifies ordering."""
    rnd = random.Random(42)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset (drive on falling edge like the reference)
    await FallingEdge(dut.clk)
    dut.rst.value = 1
    dut.inp_v.value = 0
    dut.inp_d.value = 0
    dut.out_r.value = 0
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await FallingEdge(dut.clk)

    q = deque()
    inp_index = 0

    for _ in range(1000):
        g_i = rnd.uniform(0, 1) < 0.85
        g_o = rnd.uniform(0, 1) < 0.85
        data = inp_index % 256

        # Drive all inputs before sampling any combinatorial outputs.
        # inp_r on decoupled_stage depends on out_r combinatorially, so both
        # must be driven before ReadOnly lets us sample settled values.
        dut.inp_v.value = 1 if g_i else 0
        dut.inp_d.value = data
        dut.out_r.value = 1 if g_o else 0

        # Wait for combinatorial logic to settle in this timestep.
        await ReadOnly()

        inp_ready = bool(dut.inp_r.value)
        out_valid = bool(dut.out_v.value)
        out_data = int(dut.out_d.value)

        await RisingEdge(dut.clk)

        if g_i and inp_ready:
            q.append(data)
            inp_index += 1
        if out_valid and g_o:
            expected = q.popleft()
            assert out_data == expected, f"Got {out_data}, expected {expected}"

        await FallingEdge(dut.clk)
