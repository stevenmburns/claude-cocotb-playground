import os

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge

CLK_PERIOD_NS = 20  # 50 MHz
I2C_HALF = 5  # clocks per SCL half-period (> 2-cycle sync latency in i2c_target)
I2C_ADDR = 0x08
RESULT_READY_MAX_CYCLES = 20_000_000  # enough for worst-case 24-bit subtraction GCD


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
        await RisingEdge(dut.clk)

    # Release SDA for ACK; sample o_sda_oe: target pulls low (OE=1) to ACK
    dut.i2c_sda_in.value = 1
    await _half(dut)
    dut.i2c_scl.value = 1
    await _half(dut)
    acked = bool(dut.i2c_sda_oe.value)
    dut.i2c_scl.value = 0
    await _half(dut)
    return acked


async def i2c_read_byte(dut, send_ack=True):
    """Read 8 bits from target; master drives ACK/NACK after the byte."""
    byte = 0
    for _ in range(8):
        dut.i2c_sda_in.value = 1
        await _half(dut)
        dut.i2c_scl.value = 1
        await _half(dut)
        bit = 0 if dut.i2c_sda_oe.value else 1
        byte = (byte << 1) | bit
        dut.i2c_scl.value = 0
        await RisingEdge(dut.clk)

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
    await i2c_write_byte(dut, (I2C_ADDR << 1) | 0)
    await i2c_write_byte(dut, data_byte)
    await i2c_stop(dut)


async def i2c_read_transaction(dut):
    """START + [addr+R] + read 1 byte (NACK) + STOP. Returns the byte."""
    await i2c_start(dut)
    await i2c_write_byte(dut, (I2C_ADDR << 1) | 1)
    result = await i2c_read_byte(dut, send_ack=False)
    await i2c_stop(dut)
    return result


async def send_24bit(dut, val):
    """Send a 24-bit value as 3 I2C write transactions, LSB first."""
    await i2c_write_transaction(dut, val & 0xFF)
    await i2c_write_transaction(dut, (val >> 8) & 0xFF)
    await i2c_write_transaction(dut, (val >> 16) & 0xFF)


async def read_24bit(dut):
    """Read a 24-bit value as 3 I2C read transactions, LSB first."""
    b0 = await i2c_read_transaction(dut)
    b1 = await i2c_read_transaction(dut)
    b2 = await i2c_read_transaction(dut)
    return b0 | (b1 << 8) | (b2 << 16)


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
    for _ in range(16):
        await RisingEdge(dut.clk)

    await send_24bit(dut, a)
    await send_24bit(dut, b)

    # Poll result_ready (level-sensitive)
    for _ in range(RESULT_READY_MAX_CYCLES):
        if dut.result_ready.value:
            break
        await RisingEdge(dut.clk)
    else:
        assert False, f"Timeout: result_ready never asserted for GCD({a},{b})"

    result = await read_24bit(dut)

    assert result == expected, f"GCD({a},{b}): expected {expected}, got {result}"
