# Vicharak Shrike — FPGA Pin Mapping

Complete GPIO-to-IOB coordinate mapping for the SLG47910V FPGA on the
Vicharak Shrike board. All coordinates verified from a `pins.csv` export
in Go Configure Software Hub (March 2026).

The authoritative raw data is in
`fpga/shrike/static_pins/shrike_project/static_pins/pins.csv`.

---

## GPIO Pin Table

Each FPGA GPIO has three IOB signals: `_out0` (data), `_out1` (output
enable), `_in0` (input). The IOB coordinate format is
`IOB_t[0:0]_xy[X:Y]_{out0|out1|in0}`.

### Left-side GPIOs (x = 0)

| GPIO  | PIN | IOB xy | Board label | RP2040 connection |
|-------|-----|--------|-------------|-------------------|
| GPIO0 | 13  | [0:6]  | FPGA_IO0    | —                 |
| GPIO1 | 14  | [0:7]  | FPGA_IO1    | —                 |
| GPIO2 | 15  | [0:8]  |             | —                 |
| GPIO3 | 16  | [0:9]  |             | —                 |
| GPIO4 | 17  | [0:10] |             | GPIO15 (PCB, 0-ohm resistor) |
| GPIO5 | 18  | [0:22] |             | GPIO14 (PCB, 0-ohm resistor) |
| GPIO6 | 19  | [0:23] |             | —                 |
| GPIO7 | 20  | [0:24] |             | —                 |

Note: GPIO5–7 have a gap in the y-coordinate sequence (10 → 22).

### Right-side GPIOs (x = 31)

| GPIO   | PIN | IOB xy  | Board label | RP2040 connection            |
|--------|-----|---------|-------------|------------------------------|
| GPIO8  | 23  | [31:27] |             | —                            |
| GPIO9  | 24  | [31:26] |             | —                            |
| GPIO10 |  1  | [31:25] |             | —                            |
| GPIO11 |  2  | [31:24] |             | —                            |
| GPIO12 |  3  | [31:23] |             | GPIO2 (PCB trace)            |
| GPIO13 |  4  | [31:22] |             | GPIO1 (PCB trace, bidirectional) |
| GPIO14 |  5  | [31:9]  |             | GPIO3 (PCB trace)            |
| GPIO15 |  6  | [31:8]  |             | GPIO0 (PCB trace, bidirectional) |
| GPIO16 |  7  | [31:6]  |             | —                            |
| GPIO17 |  8  | [31:5]  |             | —                            |
| GPIO18 |  9  | [31:4]  |             | —                            |

Note: GPIO14 breaks the linear y-pattern (22 → 9, not 15 as previously
assumed). GPIO8–9 y-values also skip (27, 26).

### Special pins

| Function  | IOB coordinate         | Notes                          |
|-----------|------------------------|--------------------------------|
| CLK       | `CLK_t[0:0]_W_in0`    | 50 MHz on-chip oscillator      |
| OSC_EN    | `IOB_t[0:0]_xy[0:25]_out0` | Must be driven high for clock |
| nRST      | `[31:10]_in0`          | PIN 11 input                   |
| nSLEEP    | `[31:10]_in1`          | PIN 10 input                   |
| FPGA LED  | `[31:6]_out0`          | GPIO16 / PIN 7                 |

---

## RP2040 ↔ FPGA Internal Bus

Eight pins connect the RP2040 to the FPGA via internal PCB traces. Two are
control pins (EN, PWR); the remaining six form the IO bus. Of the six IO
pins, four are dual-purpose — they serve as SPI configuration pins during
FPGA programming, then become general IO afterward.

Source: [Shrike pinout docs](https://vicharak-in.github.io/shrike/shrike_pinouts.html)

### Control pins

| RP2040 GPIO | FPGA PIN | Function |
|-------------|----------|----------|
| GPIO12      | PWR      | FPGA power control / reset |
| GPIO13      | EN       | FPGA enable (initialization control) |

### IO bus (6 pins)

| RP2040 GPIO | FPGA PIN | FPGA GPIO | Config function | Post-config use       |
|-------------|----------|-----------|------------------|-----------------------|
| GPIO0       | 6        | GPIO15    | SPI_SO (MISO)    | UART TX / SCK / SCL   |
| GPIO1       | 4        | GPIO13    | SPI_SS           | UART RX / MOSI / SDA  |
| GPIO2       | 3        | GPIO12    | SPI_SCLK         | SS_N                  |
| GPIO3       | 5        | GPIO14    | SPI_SI (MOSI)    | MISO / result_ready   |
| GPIO14      | 18       | GPIO5     | —                | GPIO (0-ohm resistor) |
| GPIO15      | 17       | GPIO4     | —                | GPIO (0-ohm resistor) |

The first four pins (GPIO0–3) are dual-purpose: used for SPI configuration
during FPGA programming, then available as general IO. RP2040 GPIO2 and
GPIO3 (FPGA PINs 3, 5) require **external jumper wires** from the RP2040
header to the FPGA header for SPI MISO and SS_N use cases.

The last two pins (GPIO14, GPIO15 → FPGA PINs 17, 18) are connected via
0-ohm resistors on the PCB. The Shrike docs advise against using these as
IO headers unless the resistor configuration has been verified or modified.

---

## RP2040 Header Pins

The RP2040 exposes additional GPIOs on the board header:

| Board label | RP2040 GPIO | Alternate functions               |
|-------------|-------------|-----------------------------------|
| RP_IO5      | GPIO5       | I2C0 SCL, UART1 RX, SPI0 CSn     |
| RP_IO6      | GPIO6       | I2C0 SDA, UART1 TX, SPI0 SCK     |

These are useful for driving test signals to FPGA inputs via jumper wires.

---

## gen_ffpga.py Symbolic Names

The `gen_ffpga.py` script accepts symbolic pin names. The full table is in
the `KNOWN_PINS` dict. Pattern: `GPIO<N>_OUT0`, `GPIO<N>_OUT1`,
`GPIO<N>_IN` for any N in 0–18, plus `CLK` and `OSC_EN`.

```sh
python fpga/shrike/gen_ffpga.py --list-pins
```

---

## Verilog Annotations for ForgeFPGA

All designs targeting the Shrike must include:

```verilog
(* top *)
module my_design (
    (* iopad_external_pin, clkbuf_inhibit *) input  wire clk,
    (* iopad_external_pin *)                 output wire clk_en,
    (* iopad_external_pin *)                 input  wire some_input,
    (* iopad_external_pin *)                 output wire some_output,
    (* iopad_external_pin *)                 output wire some_output_oe
);
    assign clk_en = 1'b1;  // enable the on-chip oscillator
```

- `(* top *)` marks the top-level module for Yosys
- `(* iopad_external_pin *)` on every port for correct IO placement
- `(* clkbuf_inhibit *)` on the clock input to prevent buffer insertion
- `clk` + `clk_en` are required even for combinational logic — the
  place-and-route tool fails without them

---

## Hardware-Verified Designs

| Design      | Status | Outputs verified on          |
|-------------|--------|------------------------------|
| static_pins | working | GPIO0=0, GPIO1=1 (logic analyser) |
| counter     | working | 100 KHz / 50 KHz on GPIO0/GPIO1   |
| and_gate    | built  | not yet verified (possible wiring error) |
| uart_gcd    | built  | not yet verified on hardware |
| spi_gcd     | built  | not yet verified on hardware |
| i2c_gcd     | built  | not yet verified on hardware |
