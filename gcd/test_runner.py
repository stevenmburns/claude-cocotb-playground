import math
import subprocess
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis.strategies import integers
from cocotb_tools.runner import get_runner

TESTS_DIR = Path(__file__).parent
SIM_BUILD = TESTS_DIR / "sim_build"

MAX = 2**12 - 1  # 4095

KNOWN_CASES = [
    pytest.param(48, 18, 6, id="48_18"),
    pytest.param(100, 75, 25, id="100_75"),
    pytest.param(1, 1, 1, id="1_1"),
    pytest.param(7, 0, 7, id="7_0"),
    pytest.param(0, 5, 5, id="0_5"),
    pytest.param(256, 16, 16, id="pow2"),
    pytest.param(4094, 4093, 1, id="consecutive"),
    pytest.param(3584, 2688, 896, id="large"),
]


BUILD_LOG = SIM_BUILD / "build.log"


@pytest.fixture(scope="session")
def built_gcd():
    runner = get_runner("verilator")
    BUILD_LOG.parent.mkdir(exist_ok=True)
    runner.build(
        sources=[TESTS_DIR / "gcd.v"],
        hdl_toplevel="gcd",
        build_args=["--timing", "--coverage"],
        always=True,
        waves=True,
        log_file=BUILD_LOG,
    )
    return runner


@pytest.fixture(autouse=True)
def capture_coverage(request):
    """Rename coverage.dat after each test so runs don't overwrite each other."""
    yield
    coverage_dat = SIM_BUILD / "coverage.dat"
    if coverage_dat.exists():
        safe_name = request.node.name.replace("[", "_").replace("]", "")
        coverage_dat.rename(SIM_BUILD / f"cov_{safe_name}.dat")


@pytest.fixture(scope="session", autouse=True)
def generate_coverage_report():
    """Merge per-test coverage files and produce an annotated report."""
    yield
    if not SIM_BUILD.exists():
        return
    dat_files = sorted(SIM_BUILD.glob("cov_*.dat"))
    if not dat_files:
        return
    annotated = SIM_BUILD / "coverage_annotated"
    annotated.mkdir(exist_ok=True)
    subprocess.run(
        [
            "verilator_coverage",
            "--annotate",
            str(annotated),
            *[str(f) for f in dat_files],
        ],
        check=False,
    )


def _run(runner, a, b, expected, waves=False):
    runner.test(
        hdl_toplevel="gcd",
        test_module="test_gcd",
        extra_env={"GCD_A": str(a), "GCD_B": str(b), "GCD_EXPECTED": str(expected)},
        waves=waves,
    )


@pytest.mark.parametrize("a,b,expected", KNOWN_CASES)
def test_gcd_known(built_gcd, a, b, expected):
    _run(built_gcd, a, b, expected, waves=True)


@given(
    a=integers(min_value=0, max_value=MAX),
    b=integers(min_value=0, max_value=MAX),
)
@settings(max_examples=20, deadline=None)
def test_gcd_hypothesis(built_gcd, a, b):
    _run(built_gcd, a, b, math.gcd(a, b))
