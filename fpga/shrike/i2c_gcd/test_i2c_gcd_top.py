import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CLK_PERIOD_NS = 20  # 50 MHz
I2C_HALF = 5  # clocks per SCL half-period (> 2-cycle sync latency in i2c_target)
I2C_ADDR = 0x08
RESULT_READY_MAX_CYCLES = 5000  # enough for worst-case GCD(255,1)


async def _half(dut):
    """Wait one SCL half-period."""
    for _ in range(I2C_HALF):
        await RisingEdge(dut.clk)


async def i2c_start(dut):
    """Generate I2C START condition: SDA falls while SCL high, then SCL falls."""
    dut.i2c_sda_in.value = 0
    await _half(dut)
    dut.i2c_scl.value = 0
    await _half(dut)


async def i2c_stop(dut):
    """Generate I2C STOP condition: SCL rises, then SDA rises while SCL high."""
    dut.i2c_sda_in.value = 0
    await _half(dut)
    dut.i2c_scl.value = 1
    await _half(dut)
    dut.i2c_sda_in.value = 1
    await _half(dut)


async def i2c_write_byte(dut, data):
    """Drive 8 bits MSB-first; read ACK from target (returns True if ACKed)."""
    for i in range(7, -1, -1):
        bit = (data >> i) & 1
        dut.i2c_sda_in.value = bit
        await _half(dut)
        dut.i2c_scl.value = 1
        await _half(dut)
        dut.i2c_scl.value = 0
        await RisingEdge(
            dut.clk
        )  # delay SDA change from SCL fall to avoid spurious START/STOP in i2c_target sync

    # Release SDA for ACK; sample o_sda_oe: target pulls low (OE=1) to ACK
    dut.i2c_sda_in.value = 1
    await _half(dut)
    dut.i2c_scl.value = 1
    await _half(dut)
    acked = bool(dut.i2c_sda_oe.value)  # OE=1 means target is pulling SDA low (ACK)
    dut.i2c_scl.value = 0
    await _half(dut)
    return acked


async def i2c_read_byte(dut, send_ack=True):
    """Read 8 bits from target; master drives ACK/NACK after the byte."""
    byte = 0
    for _ in range(8):
        dut.i2c_sda_in.value = 1  # release SDA
        await _half(dut)
        dut.i2c_scl.value = 1
        await _half(dut)
        # When o_sda_oe=1, target is pulling SDA low → bit=0; else bit=1
        bit = 0 if dut.i2c_sda_oe.value else 1
        byte = (byte << 1) | bit
        dut.i2c_scl.value = 0
        await RisingEdge(
            dut.clk
        )  # delay SDA change from SCL fall to avoid spurious START/STOP in i2c_target sync

    # Master drives ACK (SDA=0) or NACK (SDA=1)
    dut.i2c_sda_in.value = 0 if send_ack else 1
    await _half(dut)
    dut.i2c_scl.value = 1
    await _half(dut)
    dut.i2c_scl.value = 0
    await _half(dut)
    return byte


async def i2c_write_transaction(dut, data_byte):
    """START + [addr+W] + data_byte + STOP."""
    await i2c_start(dut)
    await i2c_write_byte(dut, (I2C_ADDR << 1) | 0)  # addr + W
    await i2c_write_byte(dut, data_byte)
    await i2c_stop(dut)


async def i2c_read_transaction(dut):
    """START + [addr+R] + read 1 byte (NACK) + STOP. Returns the byte."""
    await i2c_start(dut)
    await i2c_write_byte(dut, (I2C_ADDR << 1) | 1)  # addr + R
    result = await i2c_read_byte(dut, send_ack=False)  # NACK after single byte
    await i2c_stop(dut)
    return result


@cocotb.test()
async def test_gcd_i2c(dut):
    a = int(os.environ["GCD_A"])
    b = int(os.environ["GCD_B"])
    expected = int(os.environ["GCD_EXPECTED"])

    cocotb.start_soon(Clock(dut.clk, CLK_PERIOD_NS, unit="ns").start())

    # Idle state: both lines high (open-drain default)
    dut.i2c_scl.value = 1
    dut.i2c_sda_in.value = 1

    # External reset: assert for 16 cycles, then release
    dut.ext_rst.value = 1
    for _ in range(16):
        await RisingEdge(dut.clk)
    dut.ext_rst.value = 0
    # Wait for synchroniser to propagate (2 cycles) + margin
    for _ in range(16):
        await RisingEdge(dut.clk)

    await i2c_write_transaction(dut, a)  # send a
    await i2c_write_transaction(dut, b)  # send b; GCD starts

    # Poll result_ready (level-sensitive) — avoids missing the signal if GCD
    # finishes before we reach the await, while still bounding the VCD size.
    for _ in range(RESULT_READY_MAX_CYCLES):
        if dut.result_ready.value:
            break
        await RisingEdge(dut.clk)
    else:
        assert False, f"Timeout: result_ready never asserted for GCD({a},{b})"

    result = await i2c_read_transaction(dut)

    assert result == expected, f"GCD({a},{b}): expected {expected}, got {result}"
