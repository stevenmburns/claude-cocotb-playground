# i2c_test.py — automated 8-bit I2C GCD test with external reset + IRQ
#
# Wiring:
#   RP2040 GPIO2  → FPGA GPIO3 (PIN 16) = ext_rst      (PCB trace)
#   RP2040 GPIO5  → FPGA GPIO0 (PIN 13) = i2c_scl      (jumper: RP_IO5 → FPGA_IO0)
#   RP2040 GPIO8  ↔ FPGA GPIO1 (PIN 14) = i2c_sda      (jumper: RP_IO8 → FPGA_IO1)
#   RP2040 GPIO9  ← FPGA GPIO2 (PIN 15) = result_ready (jumper: RP_IO9 → PIN 15)
#
# Uses hardware I2C0: GPIO5=I2C0_SCL, GPIO8=I2C0_SDA.
# Uses result_ready IRQ (rising edge) instead of polling or delay.

from machine import I2C, Pin
import time

I2C_ADDR = 0x08
TIMEOUT_MS = 5000

# External reset: hold high, init peripherals, then release
rst = Pin(2, Pin.OUT, value=1)

i2c = I2C(0, scl=Pin(5), sda=Pin(8), freq=100_000)

# result_ready IRQ setup
_result_flag = False


def _on_result_ready(pin):
    global _result_flag
    _result_flag = True


result_pin = Pin(9, Pin.IN)
result_pin.irq(trigger=Pin.IRQ_RISING, handler=_on_result_ready)

# Release reset
time.sleep_ms(100)
rst(0)
time.sleep_ms(100)


def gcd_fpga(a, b):
    """Send a, b over I2C; wait for result_ready IRQ; read result."""
    global _result_flag
    _result_flag = False

    i2c.writeto(I2C_ADDR, bytes([a & 0xFF]))
    i2c.writeto(I2C_ADDR, bytes([b & 0xFF]))

    # Wait for result_ready rising edge (IRQ sets flag)
    start = time.ticks_ms()
    while not _result_flag:
        if time.ticks_diff(time.ticks_ms(), start) > TIMEOUT_MS:
            return None
        time.sleep_ms(1)

    return i2c.readfrom(I2C_ADDR, 1)[0]


test_cases = [
    (12, 8, 4),
    (48, 18, 6),
    (0, 5, 5),
    (7, 0, 7),
    (1, 1, 1),
    (255, 170, 85),
    (100, 75, 25),
    (255, 1, 1),      # worst case for 8-bit subtraction GCD
]

print("8-bit I2C GCD hardware test")
print("I2C0 SCL=GPIO5 SDA=GPIO8, reset=GPIO2, result_ready=GPIO9")
print()

# Scan for target
found = i2c.scan()
if I2C_ADDR in found:
    print("I2C target 0x{:02X} found".format(I2C_ADDR))
else:
    print("WARNING: target 0x{:02X} not found (scan={})".format(
        I2C_ADDR, [hex(a) for a in found]))
print()

ok = 0
for a, b, expected in test_cases:
    got = gcd_fpga(a, b)
    if got is None:
        status = "TIMEOUT"
    elif got == expected:
        status = "OK"
        ok += 1
    else:
        status = "FAIL (expected {})".format(expected)
    print("  gcd({}, {}) = {} — {}".format(a, b, got, status))

print("\n{}/{} passed".format(ok, len(test_cases)))
