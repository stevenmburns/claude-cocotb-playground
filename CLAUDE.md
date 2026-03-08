# cocotb Playground Memory

## Environment
- Python 3.12 venv at `.venv` (project root)
- cocotb 2.0.1 installed in venv
- pytest 9.0.2, hypothesis 6.151.9, vcdvcd 2.6.0, matplotlib 3.10.8 installed in venv
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
- `runner.test()` accepts `extra_env` dict to pass env vars into the simulation subprocess
- `MODULE` Makefile var deprecated; use `COCOTB_TEST_MODULES`

## IPC Pattern (runner ↔ testbench)
- Config in: `COCOTB_SCHEDULE` env var (JSON string), passed via `extra_env=` on `runner.test()`
- Results out: `STATS_PATH` env var points to `sim_build/<dut>/stats.json`, written by testbench on exit
- `_test_env(dut_subdir)` helper in `test_runner.py` builds this dict

## FIFO Schedule Format
`COCOTB_SCHEDULE` is a JSON list of phase dicts:
```json
{"g_i": 0.85, "g_o": 0.85, "until": {"kind": "cycles", "count": 1000}, "timeout_cycles": 1001}
```
- `until.kind`: `"cycles"` | `"inp_handshakes"` | `"out_handshakes"` | `"drained"`
- For count-based kinds, `timeout` is auto-raised to `target+1` to avoid off-by-one
- Default schedule: 1000 traffic cycles (g_i=0.85, g_o=0.85) then drain (g_i=0.0)

## Test Architecture (fifo/)
DUTs: `fifo`, `decoupled_stage`, `moore_stage`, `decoupled_stage_array`, `moore_stage_array`,
      `half_stage_wrap`, `half_stage_array`, `blocked_stage_wrap`, `blocked_stage_array` — 11 tests total
      (`fifo` DUT also has `test_fifo_empty` and `test_fifo_fill_drain` boundary tests)

- `test_fifo.py` — `HandshakeStats` class records per-cycle timestamps; `run_phase()` drives one schedule phase; `test_random_traffic` loops phases and writes `stats.json`
- `test_runner.py` — session build fixtures + `_test_env()` helper; `capture_coverage`, `generate_coverage_report`, `verify_stats_vs_vcd` session fixtures
- `verify_stats_vs_vcd` — after all tests, asserts `inp_count`, `out_count`, and `latencies` from inline stats match `analyze_vcd.analyze()` on the VCD (latencies are differences so reset-cycle offset cancels)
- `analyze_vcd.py` — `analyze(vcd_path)` is importable; `matplotlib` import deferred inside `main()` so CI (no matplotlib) can still use `analyze()`

## New DUT Families (HalfStage / BlockedStage)
- Chisel-generated port names: `clock`/`reset`, `io_inp_ready/valid/bits`, `io_out_ready/valid/bits`, 16-bit width
- Thin wrappers (`half_stage_wrap.v`, `blocked_stage_wrap.v`) adapt to testbench convention
- HalfStage: `inp_r = ~out_valid` — no comb path; array uses unpacked wires (no UNOPTFLAT)
- BlockedStage: `inp_r = out_r` — comb chain; array uses packed wires + `lint_off UNOPTFLAT`
- Testbench sends 8-bit data (0–255) over 16-bit wires; zero-extension means assertions still hold

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
- Jobs: `lint` (ruff check .), `test` (pytest gcd/test_runner.py + fifo/test_runner.py -v --tb=short), `deploy-pages` (coverage HTML)
- Verilator 5.046 built from source, cached at `~/.local` with key `verilator-5.046-ubuntu-latest`
- apt packages (libfl2, g++, etc.) are ALWAYS installed — only the Verilator build is skipped on cache hit
  - Lesson learned: skipping apt install on cache hit caused `make -f Vtop.mk` to fail (missing runtime libs)
- Cache hit reduces test job from ~6min to ~39s
- On failure, sim_build/build.log is uploaded as artifact `sim-build-log`
- Artifacts: `gcd-waveform`, `gcd-coverage`, `fifo-coverage`, `sim-build-log` (on failure)
- Python deps installed via: `pip install cocotb pytest hypothesis vcdvcd` (no requirements.txt; matplotlib not in CI)
