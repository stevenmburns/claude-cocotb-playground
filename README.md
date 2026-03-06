# cocotb Playground

A sandbox for experimenting with [cocotb](https://www.cocotb.org/) and [Verilator](https://www.veripool.org/verilator/).

## Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12 | |
| Verilator | ≥ 5.036 | cocotb 2.0 requirement; see install notes below |

### Install Verilator from source

The distro package is typically too old. Build 5.046 locally:

```sh
git clone --depth 1 --branch v5.046 https://github.com/verilator/verilator.git /tmp/verilator-build
cd /tmp/verilator-build
autoconf
./configure --prefix="$HOME/.local"   # or any prefix you prefer
make -j$(nproc)
make install
```

Make sure `$HOME/.local/bin` is on your `PATH`.

### Set up the Python environment

```sh
python3.12 -m venv .venv
.venv/bin/pip install cocotb
```

## Running tests

Each example directory contains a `run.sh` that sets the required `PATH` entries and delegates to `make`:

```sh
cd gcd
./run.sh        # build + run all tests
./run.sh clean  # remove build artefacts
```

## Examples

### `gcd/` — 64-bit GCD

An iterative Euclidean GCD module in Verilog with a cocotb testbench.

**Ports**

| Signal | Dir | Width | Description |
|--------|-----|-------|-------------|
| `clk` | in | 1 | Clock |
| `rst` | in | 1 | Synchronous reset |
| `start` | in | 1 | Pulse high for one cycle to begin computation |
| `a`, `b` | in | 64 | Unsigned inputs |
| `result` | out | 64 | GCD of `a` and `b` |
| `done` | out | 1 | High for one cycle when result is valid |

**Tests**
- `test_basic` — small known-value cases including zeros
- `test_large` — 64-bit inputs cross-checked against `math.gcd`

## License

MIT — see [LICENSE](LICENSE).
