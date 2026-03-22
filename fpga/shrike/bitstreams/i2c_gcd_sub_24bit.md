---
project: i2c_gcd
gcd_module: gcd (subtraction)
width: 24
source_commit: 6815e6b
build_date: 2026-03-22
utilization: 55% logic, 46% LUT, 18% FF
cells: 430 (194 FDRE, 10 FDSE, 16 CARRY4, 6 INV, 204 LUT)
p_and_r_time: ~215s
---

# i2c_gcd_sub_24bit.bin

24-bit subtraction-based GCD (Euclidean) over I2C, targeting the Vicharak
Shrike SLG47910V FPGA.

## Protocol

I2C target address 0x08, 100 kHz. All values LSB first, one byte per
I2C transaction.

1. Host → FPGA: 3 write transactions (operand a, LSB first)
2. Host → FPGA: 3 write transactions (operand b, LSB first)
3. Wait for `result_ready` rising edge (GPIO9 IRQ)
4. FPGA → Host: 3 read transactions (result = gcd(a, b), LSB first)

## Pin Mapping

| Signal         | FPGA GPIO | FPGA PIN | IOB xy  | RP2040       | Connection  |
|----------------|-----------|----------|---------|--------------|-------------|
| clk            | —         | —        | CLK W   | —            | on-chip osc |
| clk_en         | —         | —        | [0:25]  | —            | OSC_EN      |
| ext_rst        | GPIO3     | 16       | [0:9]   | GPIO2        | PCB trace   |
| i2c_scl        | GPIO0     | 13       | [0:6]   | GPIO5 (SCL)  | jumper wire |
| i2c_sda        | GPIO1     | 14       | [0:7]   | GPIO8 (SDA)  | jumper wire |
| result_ready   | GPIO2     | 15       | [0:8]   | GPIO9 (IRQ)  | jumper wire |

RP2040 uses hardware I2C0: GPIO5=I2C0_SCL, GPIO8=I2C0_SDA.

## Source Files

- `fpga/shrike/i2c_gcd/i2c_gcd_top.v` — top-level FSM (3-byte RX/TX)
- `fpga/shrike/i2c_gcd/i2c_target.v` — Renesas I2C target reference design
- `gcd/gcd.v` — subtraction-based Euclidean GCD, WIDTH=24

## gen_ffpga.py Command

```sh
python fpga/shrike/gen_ffpga.py i2c_gcd \
    --src fpga/shrike/i2c_gcd/i2c_gcd_top.v \
    --src fpga/shrike/i2c_gcd/i2c_target.v \
    --src gcd/gcd.v \
    --pin clk:CLK --pin clk_en:OSC_EN \
    --pin ext_rst:GPIO3_IN \
    --pin i2c_scl:GPIO0_IN \
    --pin i2c_sda_in:GPIO1_IN \
    --pin i2c_sda_out:GPIO1_OUT0 --pin i2c_sda_oe:GPIO1_OUT1 \
    --pin result_ready:GPIO2_OUT0 --pin result_ready_oe:GPIO2_OUT1 \
    --out fpga/shrike/i2c_gcd/shrike_project
```

## Hardware Test Results

10/10 passed (MicroPython `i2c_test.py`):

```
gcd(12, 8) = 4                         (4ms)
gcd(48, 18) = 6                        (3ms)
gcd(0, 5) = 5                          (4ms)
gcd(7, 0) = 7                          (3ms)
gcd(1, 1) = 1                          (3ms)
gcd(255, 170) = 85                     (3ms)
gcd(1000000, 750000) = 250000          (4ms)
gcd(123456, 7890) = 6                  (4ms)
gcd(16777215, 16777215) = 16777215     (3ms)
gcd(16777215, 1) = 1                   (339ms) ← worst case
```

## Flash Procedure

```sh
# Using mpremote:
mpremote cp fpga/shrike/bitstreams/i2c_gcd_sub_24bit.bin :FPGA_bitstream_MCU.bin
mpremote exec "import shrike; shrike.flash('/FPGA_bitstream_MCU.bin')"

# Or via build_and_flash.sh (rebuilds from source):
./fpga/shrike/build_and_flash.sh \
    fpga/shrike/i2c_gcd/shrike_project/i2c_gcd/i2c_gcd.ffpga \
    fpga/shrike/i2c_gcd/micropython/i2c_test.py
```
