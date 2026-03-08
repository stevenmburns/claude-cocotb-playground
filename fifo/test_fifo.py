import cocotb
import json
import os
import random
from collections import deque
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, ReadOnly

DEFAULT_SCHEDULE = [
    {
        "g_i": 0.85,
        "g_o": 0.85,
        "until": {"kind": "cycles", "count": 1000},
        "timeout_cycles": 1001,
    },
    {"g_i": 0.0, "g_o": 0.85, "until": {"kind": "drained"}, "timeout_cycles": 2000},
]


class HandshakeStats:
    def __init__(self):
        self.inp_cycles: list[int] = []
        self.out_cycles: list[int] = []

    def record_inp(self, cycle: int):
        self.inp_cycles.append(cycle)

    def record_out(self, cycle: int):
        self.out_cycles.append(cycle)

    def compute(self) -> dict:
        n = min(len(self.inp_cycles), len(self.out_cycles))
        lats = [self.out_cycles[i] - self.inp_cycles[i] for i in range(n)]
        s = sorted(lats)
        return {
            "inp_count": len(self.inp_cycles),
            "out_count": len(self.out_cycles),
            "latencies": lats,
            "median_latency": s[n // 2] if s else None,
            "max_latency": s[-1] if s else None,
        }


async def run_phase(dut, phase, q, stats, rnd, inp_index, cycle_offset):
    kind = phase["until"]["kind"]
    target = phase["until"].get("count", 0)
    timeout = phase.get("timeout_cycles", max(target * 4, 500) if target else 500)
    # For count-based termination the done check fires at _cycle == target,
    # so range must reach at least target+1.
    if kind in ("cycles", "inp_handshakes", "out_handshakes"):
        timeout = max(timeout, target + 1)
    g_i_prob = phase["g_i"]
    g_o_prob = phase["g_o"]
    phase_inp = 0
    phase_out = 0
    cycles_ran = 0

    for _cycle in range(timeout):
        done = (
            (kind == "cycles" and _cycle >= target)
            or (kind == "inp_handshakes" and phase_inp >= target)
            or (kind == "out_handshakes" and phase_out >= target)
            or (kind == "drained" and not q)
        )
        if done:
            break

        data = inp_index % 256
        g_i = rnd.uniform(0, 1) < g_i_prob
        g_o = rnd.uniform(0, 1) < g_o_prob

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
        cycles_ran += 1
        global_cycle = cycle_offset + _cycle

        inp_fired = g_i and inp_ready
        out_fired = out_valid and g_o

        if inp_fired:
            q.append(data)
            inp_index += 1
            phase_inp += 1
            stats.record_inp(global_cycle)
        if out_fired:
            expected = q.popleft()
            assert out_data == expected, f"Got {out_data}, expected {expected}"
            phase_out += 1
            stats.record_out(global_cycle)
    else:
        raise AssertionError(f"Phase timeout: {phase}")

    return inp_index, cycles_ran


@cocotb.test()
async def test_random_traffic(dut):
    """Schedule-driven random valid/ready traffic; deque reference model verifies ordering."""
    schedule = json.loads(
        os.environ.get("COCOTB_SCHEDULE", json.dumps(DEFAULT_SCHEDULE))
    )

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
    stats = HandshakeStats()
    cycle_offset = 0

    for phase in schedule:
        inp_index, cycles_ran = await run_phase(
            dut, phase, q, stats, rnd, inp_index, cycle_offset
        )
        cycle_offset += cycles_ran

    stats_path = os.environ.get("STATS_PATH")
    if stats_path:
        with open(stats_path, "w") as f:
            json.dump(stats.compute(), f, indent=2)
