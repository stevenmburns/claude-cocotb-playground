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
(115200 baud, `CLKS_PER_BIT=434`).
