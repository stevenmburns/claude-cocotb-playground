# cocotb Playground Memory

## Environment
- Python 3.12 venv at `.venv` (project root)
- cocotb 2.0.1 installed in venv
- pytest 9.0.2, hypothesis 6.151.9 installed in venv
- Verilator 5.046 built from source, installed to `~/.local/bin/verilator`
  - cocotb 2.0 requires Verilator >= 5.036
  - System apt package (5.020) is too old
  - Build: `autoconf && ./configure --prefix=/home/smburns/.local && make -j$(nproc) && make install`
- `~/.local/bin` added to PATH in `~/.bashrc`

## Running Tests (from a real shell)
```sh
# GCD — 9 tests
cd gcd && source ../.venv/bin/activate && pytest test_runner.py -v

# FIFO — 11 tests (9 DUTs × random traffic + 2 boundary tests on fifo DUT)
cd fifo && source ../.venv/bin/activate && pytest test_runner.py -v

# Run a subset by keyword
pytest test_runner.py -v -k "fifo_empty or fifo_fill_drain"
```

## CC Environment Issue (do NOT chase)
- The Claude Code Bash tool restricts `execve` when stdout is inherited (None)
- This causes `perl not found` when `runner.build()` is called from CC
- This is a sandbox artifact — works fine in a real shell
- Workarounds (log_file, monkey-patching) were investigated but not worth pursuing

## cocotb 2.0.1 API Notes
- `Clock(dut.clk, 10, unit="ns")` — argument is `unit`, not `units` (deprecated)
- `@cocotb.test()` produces `cocotb._decorators.Test` instances (has `.name` attribute)
- Makefile flow: `cocotb-config --makefiles` → `Makefile.sim` (no longer used)
- Runner flow: `cocotb_tools.runner.get_runner("verilator")` — preferred in 2.0
- `MODULE` Makefile var deprecated; use `COCOTB_TEST_MODULES`

## Test Architecture (gcd/)
- `gcd.v` — 12-bit iterative Euclidean GCD (ports: clk, rst, start, a[11:0], b[11:0], result[11:0], done)
- `test_gcd.py` — single `@cocotb.test()` reads GCD_A, GCD_B, GCD_EXPECTED from env vars
- `test_runner.py` — owns all test cases:
  - `built_gcd` session fixture: calls `runner.build()` once with `waves=True` and `--coverage`
  - `capture_coverage` autouse fixture: renames `coverage.dat` → `cov_<testname>.dat` after each test
  - `generate_coverage_report` session fixture: merges all `cov_*.dat` via `verilator_coverage --annotate` into `sim_build/coverage_annotated/`
  - `test_gcd_known`: 8 parametrized known-value cases, run with `waves=True`
  - `test_gcd_hypothesis`: Hypothesis @given with 20 examples, deadline=None
- `pytest.ini` at project root suppresses PytestCollectionWarning from cocotb internals
- VCD waveform: `sim_build/dump.vcd` (viewable in VS Code with WaveTrace extension)
- Coverage report: `sim_build/coverage_annotated/gcd.v` (annotated with hit counts)

## Project Structure
- Repo: https://github.com/stevenmburns/claude-cocotb-playground
- Branch: main
- License: MIT 2026 Steven Burns

## Future Work
- [ ] Post-synthesis simulation — run cocotb against the gate-level netlist produced by the Shrike FPGA toolchain to verify nothing was dropped or misoptimised during synthesis
- [ ] Alternative FPGA communication protocols — explore I2C and SPI interfaces as alternatives to UART for host↔FPGA communication, with corresponding cocotb pin-level testbenches

## CI (implemented, .github/workflows/ci.yml)
- Two jobs: `lint` (ruff check .) and `test` (pytest gcd/test_runner.py -v --tb=short)
- Verilator 5.046 built from source, cached at `~/.local` with key `verilator-5.046-ubuntu-latest`
- apt packages (libfl2, g++, etc.) are ALWAYS installed — only the Verilator build is skipped on cache hit
  - Lesson learned: skipping apt install on cache hit caused `make -f Vtop.mk` to fail (missing runtime libs)
- Cache hit reduces test job from ~6min to ~39s
- On failure, sim_build/build.log is uploaded as artifact `sim-build-log`
- On every run, `sim_build/dump.vcd` uploaded as `gcd-waveform` and `sim_build/coverage_annotated/` as `gcd-coverage`
- Python deps installed via: `pip install cocotb pytest hypothesis` (no requirements.txt)
