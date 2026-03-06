import math
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis.strategies import integers
from cocotb_tools.runner import get_runner

TESTS_DIR = Path(__file__).parent

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


BUILD_LOG = TESTS_DIR / "sim_build" / "build.log"


@pytest.fixture(scope="session")
def built_gcd():
    runner = get_runner("verilator")
    BUILD_LOG.parent.mkdir(exist_ok=True)
    runner.build(
        sources=[TESTS_DIR / "gcd.v"],
        hdl_toplevel="gcd",
        build_args=["--timing"],
        always=True,
        log_file=BUILD_LOG,
    )
    return runner


def _run(runner, a, b, expected):
    runner.test(
        hdl_toplevel="gcd",
        test_module="test_gcd",
        extra_env={"GCD_A": str(a), "GCD_B": str(b), "GCD_EXPECTED": str(expected)},
    )


@pytest.mark.parametrize("a,b,expected", KNOWN_CASES)
def test_gcd_known(built_gcd, a, b, expected):
    _run(built_gcd, a, b, expected)


@given(
    a=integers(min_value=0, max_value=MAX),
    b=integers(min_value=0, max_value=MAX),
)
@settings(max_examples=20, deadline=None)
def test_gcd_hypothesis(built_gcd, a, b):
    _run(built_gcd, a, b, math.gcd(a, b))
