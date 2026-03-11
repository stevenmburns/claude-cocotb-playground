# Vicharak Shrike — FPGA Pin Mapping

This document records the physical GPIO pins on the Shrike board (SLG47910V FPGA),
the ForgeFPGA IOB coordinate IDs used in `.ffpga` project files, and the
per-project signal assignments.

---

## Board GPIO Overview

The SLG47910V has 19 user-accessible GPIOs across two physical sides.

| GPIO   | PIN | Side  | Connected to RP2040 GPIO |
|--------|-----|-------|--------------------------|
| GPIO0  | 13  | Left  | —                        |
| GPIO1  | 14  | Left  | —                        |
| GPIO2  | 15  | Left  | —                        |
| GPIO3  | 16  | Left  | —                        |
| GPIO4  | 17  | Left  | —                        |
| GPIO5  | 18  | Left  | —                        |
| GPIO6  | 19  | Left  | —                        |
| GPIO7  | 20  | Left  | —                        |
| GPIO8  | 23  | —     | —                        |
| GPIO9  | 24  | —     | —                        |
| GPIO10 |  1  | Right | —                        |
| GPIO11 |  2  | Right | —                        |
| GPIO12 |  3  | Right | —                        |
| GPIO13 |  4  | Right | GPIO1 (via PCB trace)    |
| GPIO14 |  5  | Right | —                        |
| GPIO15 |  6  | Right | GPIO0 (via PCB trace)    |
| GPIO16 |  7  | Right | —                        |
| GPIO17 |  8  | Right | —                        |
| GPIO18 |  9  | Right | —                        |

RP2040–FPGA links run over internal PCB traces (no external wiring needed):
- **RP2040 GPIO0 → FPGA PIN 6** (GPIO15)  — UART TX / SoftI2C SCL / SPI SCK
- **RP2040 GPIO1 ↔ FPGA PIN 4** (GPIO13)  — UART RX / SoftI2C SDA / SPI MOSI/MISO

---

## ForgeFPGA IOB Coordinate IDs

Each IOB tile exposes up to three signals: `_in0` (input), `_out0` (data output),
`_out1` (output enable). The `x` axis is 0 (left) or 31 (right); `y` is the
position along that side.

Right-side y-values follow the linear pattern `y = 22 + 7 × (13 − N)` for GPIO N
(verified for GPIO13 and GPIO15; inferred for others).

| Symbolic name   | IOB coordinate ID                  | Verified? | Notes                          |
|-----------------|------------------------------------|-----------|--------------------------------|
| `CLK`           | `CLK_t[0:0]_W_in0`                 | ✓         | 50 MHz on-chip oscillator      |
| `GPIO15_IN`     | `IOB_t[0:0]_xy[31:8]_in0`          | ✓         | PIN 6 ← RP2040 GPIO0           |
| `GPIO15_OUT0`   | `IOB_t[0:0]_xy[31:8]_out0`         | ✓         | PIN 6 → RP2040 GPIO0           |
| `GPIO14_OUT0`   | `IOB_t[0:0]_xy[31:15]_out0`        | inferred  | PIN 5 output (debug test point)|
| `GPIO13_IN`     | `IOB_t[0:0]_xy[31:22]_in0`         | inferred  | PIN 4 ← RP2040 GPIO1           |
| `GPIO13_OUT0`   | `IOB_t[0:0]_xy[31:22]_out0`        | ✓         | PIN 4 → RP2040 GPIO1           |
| `GPIO13_OUT1`   | `IOB_t[0:0]_xy[31:22]_out1`        | ✓         | PIN 4 output enable            |
| `LEFT_P25_OUT0` | `IOB_t[0:0]_xy[0:25]_out0`         | ✓         | Left-side pos 25 (clk_en)      |

"Verified" means the coordinate appeared in a synthesised `uart_gcd.ffpga` and
produced a working bitstream. "Inferred" means it was derived from the pattern
but has not been confirmed by synthesis.

---

## Per-Project Signal Assignments

### uart_gcd

| RTL port     | Symbolic pin    | PIN | RP2040 |
|--------------|-----------------|-----|--------|
| `clk`        | CLK             | —   | —      |
| `clk_en`     | LEFT_P25_OUT0   | left-side | — |
| `uart_rx`    | GPIO15_IN       | 6   | GPIO0 TX |
| `uart_tx`    | GPIO13_OUT0     | 4   | GPIO1 RX |
| `uart_tx_oe` | GPIO13_OUT1     | 4   | (OE)   |

MicroPython: `UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))`

Regenerate: `python fpga/shrike/gen_ffpga.py uart_gcd_gen --src fpga/shrike/uart_gcd/gcd_top.v --src fpga/shrike/uart_gcd/uart_rx.v --src fpga/shrike/uart_gcd/uart_tx.v --src gcd/gcd.v --pin clk:CLK --pin uart_rx:GPIO15_IN --pin uart_tx:GPIO13_OUT0 --pin uart_tx_oe:GPIO13_OUT1 --pin clk_en:LEFT_P25_OUT0 --out fpga/shrike/shrike_project`

---

### i2c_gcd

| RTL port       | Symbolic pin    | PIN | RP2040 |
|----------------|-----------------|-----|--------|
| `clk`          | CLK             | —   | —      |
| `clk_en`       | LEFT_P25_OUT0   | left-side | — |
| `i2c_scl`      | GPIO15_IN       | 6   | GPIO0 (SoftI2C SCL) |
| `i2c_sda_in`   | GPIO13_IN ‡     | 4   | GPIO1 (SoftI2C SDA) |
| `i2c_sda_out`  | GPIO13_OUT0     | 4   | (always 0, open-drain) |
| `i2c_sda_oe`   | GPIO13_OUT1     | 4   | (OE — pulls SDA low) |
| `result_ready` | GPIO14_OUT0 ‡   | 5   | debug test point |

‡ inferred coordinate, not yet verified by synthesis.

I2C target address: `0x08`
MicroPython: `SoftI2C(scl=Pin(0), sda=Pin(1), freq=100_000)` — SoftI2C is required
because hardware I2C0 assigns SDA to GPIO0 and SCL to GPIO1, which is reversed
relative to the physical board connections.

Regenerate: `python fpga/shrike/gen_ffpga.py i2c_gcd --src fpga/shrike/i2c_gcd/i2c_gcd_top.v --src fpga/shrike/i2c_gcd/i2c_target.v --src gcd/gcd.v --pin clk:CLK --pin clk_en:LEFT_P25_OUT0 --pin i2c_scl:GPIO15_IN --pin i2c_sda_in:GPIO13_IN --pin i2c_sda_out:GPIO13_OUT0 --pin i2c_sda_oe:GPIO13_OUT1 --pin result_ready:GPIO14_OUT0 --out fpga/shrike/i2c_gcd/shrike_project`

---

### spi_gcd

No shrike_project generated yet. Planned signal assignments (SPI Mode 0):

| RTL port       | Symbolic pin | PIN | RP2040 |
|----------------|--------------|-----|--------|
| `clk`          | CLK          | —   | —      |
| `clk_en`       | LEFT_P25_OUT0 | left-side | — |
| `spi_sck`      | GPIO15_IN    | 6   | GPIO0 (SPI SCK) |
| `spi_mosi`     | GPIO13_IN ‡  | 4   | GPIO1 (SPI MOSI) |
| `spi_miso`     | GPIO13_OUT0  | 4   | GPIO1 (SPI MISO) |
| `spi_miso_oe`  | GPIO13_OUT1  | 4   | (OE)   |
| `spi_ss_n`     | TBD          | TBD | TBD    |
| `result_ready` | GPIO14_OUT0 ‡ | 5  | debug test point |

`spi_ss_n` requires a 3rd RP2040–FPGA connection; pin TBD.

---

## Workflow

```sh
# 1. Generate .ffpga project
python fpga/shrike/gen_ffpga.py <name> [--src ...] [--pin ...] --out <dir>

# 2. Synthesise
#    Open <dir>/<name>/<name>.ffpga in Renesas Go Configure Software Hub
#    → Synthesize → Generate Bitstream

# 3. Flash
python shrike-ctl.py /dev/ttyACM0 <dir>/<name>/ffpga/build/bitstream/FPGA_bitstream_MCU.bin

# 4. Run MicroPython client
#    Copy micropython/gcd_client.py to RP2040 as main.py
```
