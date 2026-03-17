import os
from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner

WAVES = os.environ.get("COCOTB_WAVES", "1") == "1"

TESTS_DIR = Path(__file__).parent
SIM_BUILD = TESTS_DIR / "sim_build"
BUILD_LOG = SIM_BUILD / "build.log"

SOURCES = [
    TESTS_DIR / "counter_top.v",
]


@pytest.fixture(scope="session")
def built():
    runner = get_runner("verilator")
    SIM_BUILD.mkdir(exist_ok=True)
    runner.build(
        sources=SOURCES,
        hdl_toplevel="counter_top",
        build_args=["--timing"],
        build_dir=SIM_BUILD,
        always=True,
        waves=WAVES,
        log_file=BUILD_LOG,
    )
    return runner


def test_counter_outputs(built):
    built.test(
        hdl_toplevel="counter_top",
        test_module="test_counter_top",
        waves=WAVES,
    )
