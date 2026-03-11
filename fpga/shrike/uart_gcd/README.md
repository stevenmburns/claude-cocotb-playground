# UART GCD — Vicharak Shrike

Runs the iterative Euclidean GCD core (`gcd/gcd.v`) on the Vicharak Shrike board.
The board pairs a Renesas SLG47910V "ForgeFPGA" with a Raspberry Pi RP2040.
The RP2040 drives the FPGA over UART using MicroPython.

## Protocol

8N1 UART @ 115200 baud (`CLKS_PER_BIT = 434`, 50 MHz on-chip oscillator):

1. Host sends byte `a` (0–255)
2. Host sends byte `b` (0–255)
3. FPGA computes `gcd(a, b)` and returns 1 byte (result)

GCD inputs are 8-bit, zero-extended to 12 bits internally.

## Hardware connections

The RP2040 and FPGA are connected by an **internal 6-bit bus on the PCB** —
no physical jumper wires are needed for UART.

| RP2040 | Direction | FPGA physical pin | FPGA GPIO | Role in gcd_top |
|--------|-----------|-------------------|-----------|-----------------|
| GPIO 0 (UART0 TX) | → | PIN 6 | GPIO15 | `uart_rx` |
| GPIO 1 (UART0 RX) | ← | PIN 4 | GPIO13 | `uart_tx` |

> FPGA GPIO15 receives the RP2040's transmit line — the names are from the
> perspective of each device, so TX on one side crosses to RX on the other.

## Files

```
uart_gcd/
├── gcd_top.v               Top-level FSM: instantiates uart_rx, uart_tx, gcd
├── uart_rx.v               Standard 8N1 UART receiver (Shrike verbatim)
├── uart_tx.v               Standard 8N1 UART transmitter (Shrike verbatim)
├── test_gcd_top.py         cocotb testbench
├── test_runner.py          pytest runner (simulation only)
├── micropython/
│   └── gcd_client.py       MicroPython firmware for RP2040
└── shrike_project/
    ├── template/
    │   └── blank.ffpga     Blank .ffpga used as template by gen_ffpga.py
    └── uart_gcd/           ForgeFPGA GUI project
        ├── uart_gcd.ffpga  GUI project file (checked in)
        └── ffpga/
            ├── src/        Symlinks to canonical Verilog (checked in)
            └── build/      Synthesis output (gitignored)
                └── bitstream/
                    └── FPGA_bitstream_MCU.bin   ← flash this file
```

The canonical Verilog lives in `uart_gcd/*.v` and `gcd/gcd.v`.
`ffpga/src/` contains relative symlinks to those files and is checked into git —
no regeneration is needed after a fresh clone.

---

## Simulation (cocotb + Verilator)

```sh
cd fpga/shrike/uart_gcd
source ../../../.venv/bin/activate
pytest test_runner.py -v
```

UART baud is overridden to `CLKS_PER_BIT = 8` for fast simulation.

---

## Hardware bring-up

### 1 — ForgeFPGA project file

`shrike_project/uart_gcd/uart_gcd.ffpga` and the `ffpga/src/` symlinks are
checked into git — no generation step is needed after a fresh clone.

To regenerate (e.g. after changing pin assignments), run from the repo root:

```sh
source .venv/bin/activate
python fpga/shrike/gen_ffpga.py uart_gcd \
    --src fpga/shrike/uart_gcd/gcd_top.v \
    --src fpga/shrike/uart_gcd/uart_rx.v \
    --src fpga/shrike/uart_gcd/uart_tx.v \
    --src gcd/gcd.v \
    --pin clk:CLK \
    --pin uart_rx:GPIO15_IN \
    --pin uart_tx:GPIO13_OUT0 \
    --pin uart_tx_oe:GPIO13_OUT1 \
    --pin clk_en:LEFT_P25_OUT0 \
    --out fpga/shrike/uart_gcd/shrike_project
```

See `gen_ffpga.py --list-pins` for all known symbolic pin names.

### 2 — Synthesize and generate bitstream (GUI)

Open `shrike_project/uart_gcd/uart_gcd.ffpga` in the Renesas
**Go Configure Software Hub** GUI.

1. Click **Synthesize**
2. Click **Generate Bitstream**

The bitstream appears at:
```
shrike_project/uart_gcd/ffpga/build/bitstream/FPGA_bitstream_MCU.bin
```

### 3 — Flash the FPGA (shrike-ctl)

Flash `shrike-ctl.uf2` to the RP2040 once (hold BOOTSEL, plug in USB,
drag-and-drop). From then on, flash new bitstreams with:

```sh
python path/to/shrike-ctl.py /dev/ttyACM0 \
    fpga/shrike/uart_gcd/shrike_project/uart_gcd/ffpga/build/bitstream/FPGA_bitstream_MCU.bin
```

`shrike-ctl` is in the [vicharak-in/shrike](https://github.com/vicharak-in/shrike)
repository under `utils/shrike-ctl/`.

After flashing the FPGA, re-flash the RP2040 with standard MicroPython firmware
before running the client.

### 4 — Run the MicroPython client

Copy `micropython/gcd_client.py` to the RP2040 as `main.py`
(e.g. via Thonny or `mpremote`), then connect to the REPL:

```
a: 48
b: 18
  gcd(48, 18) = 6

a: 255
b: 0
  gcd(255, 0) = 255
```

The client uses `UART(0, baudrate=115200, tx=Pin(0), rx=Pin(1))`.
No wiring changes are needed between sessions — the UART lines are
permanently connected on the PCB.

---

## gen_ffpga.py reference

`gen_ffpga.py` lives at `fpga/shrike/gen_ffpga.py` and works for any
Shrike project, not just uart_gcd. It reads the blank template from
`uart_gcd/shrike_project/template/blank.ffpga` and produces a
valid ForgeFPGA project file by substituting the module list and pin
assignments.

```
usage: gen_ffpga.py [-h] --src FILE --pin PORT:PIN [--out DIR]
                    [--template FILE] [--list-pins]
                    project_name

python gen_ffpga.py --list-pins   # show all known symbolic pin names
```

The `--pin PORT:PIN` syntax accepts either a symbolic name (`GPIO15_IN`)
or a raw IOB coordinate (`IOB_t[0:0]_xy[31:8]_in0`).

---

## Toolchain notes

- **Synthesis**: Renesas Go Configure Software Hub v6.52 (ForgeFPGA Workshop)
  internally uses Yosys v0.37 for synthesis and a proprietary P&R backend.
- **Bitstream format**: `FPGA_bitstream_MCU.bin` is 46408 bytes; this is the
  variant consumed by `shrike-ctl`.
- **Clock**: The `clk` port connects to the SLG47910V on-chip 50 MHz oscillator.
  Simulation overrides to `CLKS_PER_BIT = 8` via a `-G` parameter.
- **Reset**: `gcd_top.v` generates a 16-cycle power-on reset internally;
  no external reset pin is needed.
