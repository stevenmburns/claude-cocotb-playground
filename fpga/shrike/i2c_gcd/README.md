# I2C GCD — Vicharak Shrike

Implements the existing `gcd/gcd.v` (12-bit iterative Euclidean GCD) on the Vicharak Shrike
board using I2C instead of UART. The I2C target module is the Renesas reference design
(`i2c_target.v`) from the ForgeFPGA example library.

## Protocol

I2C target address `0x08`, 50 MHz on-chip oscillator:

| Step | Direction | Payload | FPGA action |
|------|-----------|---------|-------------|
| 1 | Master writes 1 byte | `a` (0–255) | Latch `reg_a` |
| 2 | Master writes 1 byte | `b` (0–255) | Start GCD computation |
| 3 | Master reads 1 byte  | — | Return `gcd(a, b)` |

After step 2, the GCD completes in microseconds at 50 MHz — a 2 ms software delay
before the read is more than sufficient. No polling of `result_ready` is needed
in the MicroPython client.

## Hardware connections

The RP2040 and FPGA are connected by an internal PCB bus — no wires needed for SCL/SDA.

| RP2040 | Direction | FPGA PIN | FPGA GPIO | Role in i2c_gcd_top |
|--------|-----------|----------|-----------|---------------------|
| GPIO0 (SoftI2C SCL) | → | PIN 6 | GPIO15 | `i2c_scl` |
| GPIO1 (SoftI2C SDA) | ↔ | PIN 4 | GPIO13 | `i2c_sda` (open-drain via OE) |

**Note:** `SoftI2C` is required on the RP2040 because hardware I2C0 assigns SDA to GPIO0
and SCL to GPIO1, which is the reverse of the physical board connections.

`result_ready` (FPGA PIN 5 / GPIO14, inferred) is a debug test point only; it is not
connected to the RP2040.

## Files

| File | Description |
|------|-------------|
| `i2c_target.v` | I2C target (Renesas reference design); `o_int_rx` and `o_int_tx` are clean 1-cycle pulses |
| `i2c_gcd_top.v` | Top-level FSM; instantiates `i2c_target` and `gcd.v` |
| `../../../gcd/gcd.v` | Shared 12-bit GCD core |
| `test_i2c_gcd_top.py` | cocotb testbench; bit-bangs I2C signals |
| `test_runner.py` | pytest runner; 6 parametrized known-value cases |
| `micropython/gcd_client.py` | MicroPython firmware for RP2040 |
| `shrike_project/i2c_gcd/` | ForgeFPGA GUI project (checked in) |

## FSM States

```
WAIT_A      → o_int_rx pulse: latch a                → WAIT_B
WAIT_B      → o_int_rx pulse: latch b                → START_GCD
START_GCD   → pulse gcd_start 1 cycle                → COMPUTING
COMPUTING   → gcd_done: latch result into tx_data_reg → WAIT_RESULT
WAIT_RESULT → o_int_tx pulse (master read done)      → WAIT_A
```

`result_ready = (state == WAIT_RESULT)`

Unlike the SPI FSM, there is no `WAIT_SS` state — `o_int_rx` and `o_int_tx` are clean
1-cycle pulses from the Renesas `i2c_target.v`, so no edge detection is needed.

## Running the Tests

```sh
cd fpga/shrike/i2c_gcd
source ../../../.venv/bin/activate
pytest test_runner.py -v
```

To capture a waveform:

```sh
COCOTB_WAVES=1 pytest test_runner.py -v -k "12_8"
# open sim_build/dump.vcd
```

## Hardware bring-up

### 1 — ForgeFPGA project file

`shrike_project/i2c_gcd/i2c_gcd.ffpga` and `ffpga/src/` symlinks are checked in —
no generation step is needed after a fresh clone.

To regenerate (from repo root):

```sh
source .venv/bin/activate
python fpga/shrike/gen_ffpga.py i2c_gcd \
    --src fpga/shrike/i2c_gcd/i2c_gcd_top.v \
    --src fpga/shrike/i2c_gcd/i2c_target.v \
    --src gcd/gcd.v \
    --pin clk:CLK \
    --pin clk_en:LEFT_P25_OUT0 \
    --pin i2c_scl:GPIO15_IN \
    --pin i2c_sda_in:GPIO13_IN \
    --pin i2c_sda_out:GPIO13_OUT0 \
    --pin i2c_sda_oe:GPIO13_OUT1 \
    --pin result_ready:GPIO14_OUT0 \
    --out fpga/shrike/i2c_gcd/shrike_project
```

### 2 — Synthesize and flash

Open `shrike_project/i2c_gcd/i2c_gcd.ffpga` in **Renesas Go Configure Software Hub**,
click **Synthesize** → **Generate Bitstream**, then:

```sh
python path/to/shrike-ctl.py /dev/ttyACM0 \
    fpga/shrike/i2c_gcd/shrike_project/i2c_gcd/ffpga/build/bitstream/FPGA_bitstream_MCU.bin
```

### 3 — Run the MicroPython client

Copy `micropython/gcd_client.py` to the RP2040 as `main.py`:

```
I2C GCD client — Vicharak Shrike
SoftI2C SCL=GPIO0 SDA=GPIO1 @ 100 kHz  addr=0x08
Enter two integers 0–255. Ctrl-C to exit.

a: 48
b: 18
  gcd(48, 18) = 6
```

## Design Notes

- `i2c_target.v` output `o_int_rx` pulses once when the master finishes writing a byte;
  `o_int_tx` pulses once when the master reads a byte. Both are already clean 1-cycle
  pulses — no edge detection needed.
- `tx_data_reg` is latched in the `COMPUTING` state (before the master issues the read
  transaction), ensuring the I2C target sees valid data in time.
- Inputs are 8-bit (0–255), zero-extended to 12 bits for the GCD core.
- Power-on reset is generated internally (16-cycle counter); no external reset pin.
- See `fpga/shrike/PIN_MAPPING.md` for full IOB coordinate documentation.
