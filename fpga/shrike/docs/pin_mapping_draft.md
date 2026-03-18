# DRAFT: Revised RP2040 ↔ FPGA Pin Mapping

**Status: UNVERIFIED — needs hardware testing before updating gen_ffpga.py**

## Background

Our original pin mapping (GPIO0→PIN 6, GPIO1→PIN 4) came from the Shrike
pinout documentation. However, examining the official Vicharak examples
(`uart_sum`, `spi_loopback_led`, `i2c_led`) reveals they use completely
different FPGA pins — all on the **left side** of the FPGA (x=0), not the
right side (x=31).

## Evidence from Vicharak Examples

### uart_sum

MicroPython: `UART(0, tx=Pin(0), rx=Pin(1))`, `reset=Pin(2)`

| Signal | RP2040 GPIO | FPGA IOB | pins.csv GPIO | PIN |
|--------|-------------|----------|---------------|-----|
| rx     | GPIO0 (TX)  | `[0:23]_in0` | GPIO6     | 19  |
| tx     | GPIO1 (RX)  | `[0:10]_out0` | GPIO4    | 17  |
| tx_en  | GPIO1 (RX)  | `[0:10]_out1` | GPIO4    | 17  |
| rst    | GPIO2       | `[0:9]_in0`  | GPIO3    | 16  |

### spi_loopback_led

MicroPython: `SPI(0, sck=Pin(2), mosi=Pin(3), miso=Pin(0))`, `cs=Pin(1)`,
`reset=Pin(14)`

| Signal   | RP2040 GPIO | FPGA IOB | pins.csv GPIO | PIN |
|----------|-------------|----------|---------------|-----|
| spi_miso | GPIO0       | `[0:23]_out0` | GPIO6    | 19  |
| spi_ss_n | GPIO1       | `[0:10]_in0`  | GPIO4    | 17  |
| spi_sck  | GPIO2       | `[0:9]_in0`   | GPIO3    | 16  |
| spi_mosi | GPIO3       | `[0:22]_in0`  | GPIO5    | 18  |
| rst_n    | GPIO14      | `[31:4]_in0`  | GPIO18   | 9   |

### i2c_led

MicroPython: (not examined yet, but FPGA mappings from .ffpga)

| Signal | FPGA IOB | pins.csv GPIO | PIN |
|--------|----------|---------------|-----|
| i_scl  | `[0:10]_in0`  | GPIO4  | 17  |
| i_sda  | `[0:23]_in0`  | GPIO6  | 19  |
| o_sda  | `[0:23]_out0` | GPIO6  | 19  |
| i_rst  | `[0:22]_in0`  | GPIO5  | 18  |

## Proposed Revised Mapping

If the examples are correct, the actual RP2040 ↔ FPGA internal bus is:

| RP2040 GPIO | FPGA GPIO | FPGA PIN | IOB xy   | SPI0 function |
|-------------|-----------|----------|----------|---------------|
| GPIO0       | GPIO6     | 19       | `[0:23]` | MISO (RX)     |
| GPIO1       | GPIO4     | 17       | `[0:10]` | CSn (TX)      |
| GPIO2       | GPIO3     | 16       | `[0:9]`  | SCK           |
| GPIO3       | GPIO5     | 18       | `[0:22]` | MOSI (TX)     |
| GPIO14      | GPIO18    | 9        | `[31:4]` | (reset / GPIO)|
| GPIO15      | ???       | ???      | ???      | (GPIO)        |

This would mean:
- All four SPI config pins route to **left-side** FPGA GPIOs (PINs 16–19)
- The right-side pins we've been using (PINs 3–6, GPIO12–15) are **not**
  connected to the RP2040 at all
- The 0-ohm resistor pin (GPIO14) connects to GPIO18 / PIN 9, not GPIO5 / PIN 18

## What This Explains

1. **Why driving RP2040 GPIO0 as output killed the FPGA** — it was fighting
   with GPIO6 (PIN 19) on the left side, not GPIO15 (PIN 6) on the right.
   But maybe it still interferes with config.

2. **Why the 0-ohm resistor path (GPIO14 → GPIO5/PIN 18) didn't work** —
   GPIO14 actually goes to GPIO18/PIN 9, not GPIO5/PIN 18.

3. **Why our uart_gcd/spi_gcd/i2c_gcd never worked on hardware** — we
   mapped signals to the right-side pins that aren't connected to the RP2040.

## Verification Plan

1. Flash the working counter (free-running, no enable) and confirm outputs
   on FPGA_IO0/IO1 (PINs 13/14) — baseline still works.

2. Build a new counter with enable mapped to `GPIO3_IN` (`[0:9]_in0` /
   PIN 16) — this is where Vicharak maps RP2040 GPIO2.

3. Drive RP2040 GPIO2 from MicroPython: `Pin(2, Pin.OUT, value=1)` — does
   the counter start?

4. If that works, try the full UART path: remap uart_gcd to use the
   Vicharak pin assignments and test with MicroPython UART(0).

## Source

Vicharak Shrike repo: https://github.com/vicharak-in/shrike/tree/main/examples
