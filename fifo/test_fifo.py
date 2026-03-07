import cocotb
import os
import random
from collections import deque
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly


@cocotb.test()
async def test_random_traffic(dut):
    """Random valid/ready each cycle; deque reference model verifies ordering."""
    g_i_prob = float(os.environ.get("G_I_PROB", "0.85"))
    g_o_prob = float(os.environ.get("G_O_PROB", "0.85"))

    rnd = random.Random(42)
    cocotb.start_soon(Clock(dut.clk, 10, unit="ns").start())

    # Reset
    await RisingEdge(dut.clk)
    dut.rst.value = 1
    dut.inp_v.value = 0
    dut.inp_d.value = 0
    dut.out_r.value = 0
    await RisingEdge(dut.clk)
    dut.rst.value = 0
    await RisingEdge(dut.clk)

    q = deque()
    inp_index = 0

    for _ in range(1000):
        g_i = rnd.uniform(0, 1) < g_i_prob
        g_o = rnd.uniform(0, 1) < g_o_prob
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

    # Drain phase: no new input, g_o still random.
    # Timeout after 2000 cycles to catch logic errors (e.g. stuck out_v).
    dut.inp_v.value = 0
    dut.inp_d.value = 0
    for _ in range(2000):
        if not q:
            break
        g_o = rnd.uniform(0, 1) < g_o_prob
        dut.out_r.value = 1 if g_o else 0
        await ReadOnly()
        out_valid = bool(dut.out_v.value)
        out_data = int(dut.out_d.value)
        await RisingEdge(dut.clk)
        if out_valid and g_o:
            expected = q.popleft()
            assert out_data == expected, f"Drain: got {out_data}, expected {expected}"
    else:
        raise AssertionError(
            f"Drain timeout: {len(q)} items still in queue after 2000 cycles"
        )
