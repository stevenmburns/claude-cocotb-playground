# Post-Synthesis Gate-Level Simulation

Runs the cocotb UART testbench against the Yosys-generated gate-level netlist
for `gcd_top`, verifying that synthesis preserved functional correctness.

## Why not in CI

The netlist and FPGA toolchain live outside this repo and are not checked in,
so these tests are run manually after re-synthesis rather than on every commit.

## External dependencies

| Path | What it is |
|------|------------|
| `/home/smburns/shrike-gcd/GCD/ffpga/build/post_synth_results.v` | Yosys post-synthesis netlist |
| `/usr/local/go-configure-sw-hub/bin/external/yosys/share/xilinx/cells_sim.v` | Xilinx primitive simulation models |

## Running

```sh
cd fpga/shrike/gcd_postsyn
source ../../../.venv/bin/activate
pytest test_runner.py -v
```

Six parametrized cases exercise the full UART protocol at the real baud rate
(9600 baud, `CLKS_PER_BIT=5208`). Expect ~1–2 minutes total.

## Speeding it up

Re-synthesise `gcd_top` with a higher baud rate (e.g. 115200, `CLKS_PER_BIT=434`)
to get ~12× faster simulation while still exercising the gate-level netlist.
Update `CLKS_PER_BIT` and `CLK_PERIOD_NS` in `test_gcd_top.py` to match.
