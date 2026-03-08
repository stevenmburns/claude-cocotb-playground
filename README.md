# cocotb Playground

A sandbox for experimenting with [cocotb](https://www.cocotb.org/) 2.0 and [Verilator](https://www.veripool.org/verilator/).

[![CI](https://github.com/stevenmburns/claude-cocotb-playground/actions/workflows/ci.yml/badge.svg)](https://github.com/stevenmburns/claude-cocotb-playground/actions/workflows/ci.yml)

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12 | |
| Verilator | ≥ 5.036 | cocotb 2.0 requirement; distro packages are often too old |

### Install Verilator from source

```sh
git clone --depth 1 --branch v5.046 https://github.com/verilator/verilator.git /tmp/verilator-build
cd /tmp/verilator-build
autoconf
./configure --prefix="$HOME/.local"
make -j$(nproc)
make install
```

Add `$HOME/.local/bin` to your `PATH` if it isn't already.

### Set up the Python environment

```sh
python3.12 -m venv .venv
.venv/bin/pip install cocotb pytest hypothesis vcdvcd
```

## Running tests

### GCD (9 tests)

```sh
cd gcd
source ../.venv/bin/activate
pytest test_runner.py -v
```

After the run you'll find:
- `sim_build/dump.vcd` — waveform from the known test cases (open with the [WaveTrace](https://marketplace.visualstudio.com/items?itemName=wavetrace.wavetrace) VS Code extension)
- `sim_build/coverage_annotated/gcd.v` — Verilog source annotated with coverage hit counts

### FIFO (11 tests)

```sh
cd fifo
source ../.venv/bin/activate
pytest test_runner.py -v
```

Tests cover 9 DUTs (fifo, decoupled_stage, moore_stage, and their array variants, plus HalfStage and BlockedStage families). The `fifo` DUT also runs two boundary-condition tests:
- `test_fifo_empty` — drives `out_r=1` for 200 cycles with no input; asserts no spurious output
- `test_fifo_fill_drain` — floods to full (`g_i=1.0, g_o=0.0`), then drains; asserts no drops

After the run, per-DUT waveforms and coverage are under `sim_build/<dut>/`.

## Examples

### `gcd/` — 12-bit GCD

An iterative Euclidean GCD module in Verilog with a cocotb testbench.

**Ports**

| Signal | Dir | Width | Description |
|--------|-----|-------|-------------|
| `clk` | in | 1 | Clock |
| `rst` | in | 1 | Synchronous reset |
| `start` | in | 1 | Pulse high for one cycle to begin computation |
| `a`, `b` | in | 12 | Unsigned inputs (0–4095) |
| `result` | out | 12 | GCD of `a` and `b` |
| `done` | out | 1 | High for one cycle when result is valid |

**Tests**
- `test_gcd_known` — 8 parametrized known-value cases (zeros, powers of two, large inputs)
- `test_gcd_hypothesis` — property-based testing via [Hypothesis](https://hypothesis.readthedocs.io/), 20 examples cross-checked against `math.gcd`

### `fpga/shrike/spi_gcd/` — GCD over SPI (Vicharak Shrike)

A parallel SPI variant of the UART GCD interface, targeting the same Vicharak Shrike board. Uses the reference `spi_target.v` from the vicharak-in/shrike repo.

**Protocol** (SPI Mode 0, MSB-first, 8-bit):
1. Host sends byte `a` (MISO ignored)
2. Host sends byte `b` (MISO ignored); FPGA waits for SS_N deassert then starts GCD
3. Host polls `result_ready` pin; when high, sends dummy `0x00` — FPGA shifts out `gcd(a,b)` on MISO

```sh
cd fpga/shrike/spi_gcd
source ../../../.venv/bin/activate
pytest test_runner.py -v   # 6 known-value tests
```

## CI

GitHub Actions runs on every push and PR to `main`:
- **lint** — `ruff check .`
- **test** — full pytest suite with Verilator (build cached by version), including FPGA UART and SPI GCD tests

Artifacts uploaded on every run: `gcd-waveform` (VCD) and `gcd-coverage` (annotated source).

## License

MIT — see [LICENSE](LICENSE).
