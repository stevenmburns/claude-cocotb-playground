"""Post-synthesis gate-level simulation of gcd_top.

Uses the Yosys-generated netlist from the Shrike FPGA toolchain together with
the Yosys Xilinx cell simulation library (cells_sim.v).  CLKS_PER_BIT is
baked into the netlist at 5208 (50 MHz / 9600 baud), so we do NOT pass
-GCLKS_PER_BIT to the build.
"""

import os
from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner

WAVES = os.environ.get("COCOTB_WAVES", "1") == "1"

TESTS_DIR = Path(__file__).parent
SIM_BUILD = TESTS_DIR / "sim_build"

NETLIST = Path("/home/smburns/shrike-gcd/GCD/ffpga/build/post_synth_results.v")
CELLS_SIM = Path(
    "/usr/local/go-configure-sw-hub/bin/external/yosys/share/xilinx/cells_sim.v"
)

SOURCES = [CELLS_SIM, NETLIST]

KNOWN_CASES = [
    pytest.param(12, 8, 4, id="12_8"),
    pytest.param(48, 18, 6, id="48_18"),
    pytest.param(0, 5, 5, id="0_5"),
    pytest.param(7, 0, 7, id="7_0"),
    pytest.param(1, 1, 1, id="1_1"),
    pytest.param(255, 170, 85, id="powers"),
]

BUILD_LOG = SIM_BUILD / "build.log"


@pytest.fixture(scope="session")
def built():
    runner = get_runner("verilator")
    SIM_BUILD.mkdir(exist_ok=True)
    runner.build(
        sources=SOURCES,
        hdl_toplevel="gcd_top",
        # No -GCLKS_PER_BIT: baked into the netlist at 5208.
        # --no-timing: suppress specify-block timing warnings from cells_sim.v.
        build_args=["--no-timing"],
        build_dir=SIM_BUILD,
        always=True,
        waves=WAVES,
        log_file=BUILD_LOG,
    )
    return runner


@pytest.mark.parametrize("a,b,expected", KNOWN_CASES)
def test_gcd_postsyn(built, a, b, expected):
    built.test(
        hdl_toplevel="gcd_top",
        test_module="test_gcd_top",
        extra_env={"GCD_A": str(a), "GCD_B": str(b), "GCD_EXPECTED": str(expected)},
        waves=WAVES,
        build_dir=SIM_BUILD,
    )
