import os
from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner

WAVES = os.environ.get("COCOTB_WAVES", "1") == "1"

TESTS_DIR = Path(__file__).parent  # fpga/shrike/gcd/
ROOT = TESTS_DIR / "../../.."  # repo root
SIM_BUILD = TESTS_DIR / "sim_build"
CLKS_PER_BIT = 8

SOURCES = [
    TESTS_DIR / "uart_rx.v",
    TESTS_DIR / "uart_tx.v",
    ROOT / "gcd/gcd.v",  # shared GCD core
    TESTS_DIR / "gcd_top.v",  # top-level (depends on all above)
]

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
        build_args=["--timing", f"-GCLKS_PER_BIT={CLKS_PER_BIT}"],
        build_dir=SIM_BUILD,
        always=True,
        waves=WAVES,
        log_file=BUILD_LOG,
    )
    return runner


@pytest.mark.parametrize("a,b,expected", KNOWN_CASES)
def test_gcd_top_known(built, a, b, expected):
    built.test(
        hdl_toplevel="gcd_top",
        test_module="test_gcd_top",
        extra_env={"GCD_A": str(a), "GCD_B": str(b), "GCD_EXPECTED": str(expected)},
        waves=WAVES,
    )
