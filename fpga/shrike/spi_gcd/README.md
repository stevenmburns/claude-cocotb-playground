# GCD over SPI — Vicharak Shrike

Implements the existing `gcd/gcd.v` (12-bit iterative Euclidean GCD) on the Vicharak Shrike
board using SPI instead of UART. The SPI target module is taken verbatim from the
[vicharak-in/shrike](https://github.com/vicharak-in/shrike) reference design.

## Protocol

SPI Mode 0 (CPOL=0, CPHA=0), MSB-first, 8-bit transactions. Each SS_N assertion = one byte.

| Transaction | MOSI | MISO | Action |
|-------------|------|------|--------|
| 1 | `a` (0–255) | don't care | FPGA stores `a` |
| 2 | `b` (0–255) | don't care | FPGA stores `b`; starts GCD after SS_N deasserts |
| 3 (when `result_ready` high) | `0x00` (dummy) | `gcd(a,b)` | FPGA shifts out result |

`result_ready` is a GPIO output — poll it before initiating transaction 3.

## Files

| File | Description |
|------|-------------|
| `spi_target.v` | SPI target (from vicharak-in/shrike); handles sync, shift register, valid pulse |
| `spi_gcd_top.v` | Top-level FSM; instantiates `spi_target` and `gcd.v` |
| `../../../gcd/gcd.v` | Shared 12-bit GCD core |
| `test_spi_gcd_top.py` | cocotb testbench; bit-bangs SPI signals |
| `test_runner.py` | pytest runner; 6 parametrized known-value cases |

## FSM States

```
WAIT_A      → rx_data_valid pulse: latch a              → WAIT_B
WAIT_B      → rx_data_valid pulse: latch b              → WAIT_SS
WAIT_SS     → SS_N deasserts (synced): transaction done → START_GCD
START_GCD   → pulse gcd_start 1 cycle                  → COMPUTING
COMPUTING   → gcd_done: latch result into tx_data_reg   → WAIT_RESULT
WAIT_RESULT → rx_data_valid pulse (3rd transaction)     → WAIT_A
```

`result_ready = (state == WAIT_RESULT)`

## Running the Tests

```sh
cd fpga/shrike/spi_gcd
source ../../../.venv/bin/activate
pytest test_runner.py -v
```

To capture a waveform (viewable with [WaveTrace](https://marketplace.visualstudio.com/items?itemName=wavetrace.wavetrace)):

```sh
COCOTB_WAVES=1 pytest test_runner.py -v -k "12_8"
# open sim_build/dump.vcd
```

## Design Notes

- `o_rx_data_valid` from `spi_target` is a **multi-cycle** signal (stays high until SS_N
  deasserts through the 2-stage synchronizer, ~10 clocks). The FSM uses a rising-edge
  detector (`rx_data_valid_pulse`) to get a clean 1-cycle strobe.
- The `WAIT_SS` state ensures SS_N is fully deasserted before `gcd_start` is asserted —
  the SPI transaction must be complete before computation begins.
- Inputs are 8-bit (0–255), zero-extended to 12 bits for the GCD core.
- Power-on reset is generated internally (16-cycle counter); no external reset pin needed.
