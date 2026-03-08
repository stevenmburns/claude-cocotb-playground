import os
from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner

WAVES = os.environ.get("COCOTB_WAVES", "1") == "1"

TESTS_DIR = Path(__file__).parent  # fpga/shrike/spi_gcd/
ROOT = TESTS_DIR / "../../.."  # repo root
SIM_BUILD = TESTS_DIR / "sim_build"

SOURCES = [
    TESTS_DIR / "spi_target.v",
    ROOT / "gcd/gcd.v",
    TESTS_DIR / "spi_gcd_top.v",
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
        hdl_toplevel="spi_gcd_top",
        build_args=["--timing"],
        build_dir=SIM_BUILD,
        always=True,
        waves=WAVES,
        log_file=BUILD_LOG,
    )
    return runner


@pytest.mark.parametrize("a,b,expected", KNOWN_CASES)
def test_spi_gcd_top_known(built, a, b, expected):
    built.test(
        hdl_toplevel="spi_gcd_top",
        test_module="test_spi_gcd_top",
        extra_env={"GCD_A": str(a), "GCD_B": str(b), "GCD_EXPECTED": str(expected)},
        waves=WAVES,
    )
