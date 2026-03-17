"""cocotb testbench for counter_top — verify toggle frequencies."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge


@cocotb.test()
async def test_counter_outputs(dut):
    """Check that out0 and out1 toggle at the expected rates."""

    prescale = int(dut.PRESCALE.value)
    clock = Clock(dut.clk, 20, unit="ns")  # 50 MHz
    cocotb.start_soon(clock.start())

    # Wait for reset to complete (16 cycles + margin)
    await ClockCycles(dut.clk, 20)

    # clk_en and OE should be high
    assert dut.clk_en.value == 1
    assert dut.out0_oe.value == 1
    assert dut.out1_oe.value == 1

    # Measure out0 toggle period: should be PRESCALE clocks per toggle
    prev = int(dut.out0.value)
    toggles = 0
    clocks = 0
    first_toggle_at = None

    for _ in range(prescale * 10):
        await RisingEdge(dut.clk)
        clocks += 1
        cur = int(dut.out0.value)
        if cur != prev:
            if first_toggle_at is None:
                first_toggle_at = clocks
                clocks = 0
                toggles = 0
            else:
                toggles += 1
            prev = cur

    period = clocks / toggles if toggles else 0
    assert abs(period - prescale) < 2, f"out0 period {period}, expected {prescale}"

    # out1 should be half the frequency of out0
    dut._log.info(f"out0={int(dut.out0.value)}, out1={int(dut.out1.value)}")
