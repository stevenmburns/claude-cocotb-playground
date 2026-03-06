import importlib.util
from pathlib import Path

import pytest
from cocotb._decorators import Test
from cocotb_tools.runner import get_runner

TESTS_DIR = Path(__file__).parent


def discover_cocotb_tests(module_file: Path) -> list[str]:
    """Return the names of all @cocotb.test() functions in *module_file*."""
    spec = importlib.util.spec_from_file_location("_cocotb_discovery", module_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [name for name, obj in vars(mod).items() if isinstance(obj, Test)]


@pytest.fixture(scope="session")
def built_gcd():
    """Build the GCD simulation once per session."""
    runner = get_runner("verilator")
    runner.build(
        sources=[TESTS_DIR / "gcd.v"],
        hdl_toplevel="gcd",
        build_args=["--timing"],
    )
    return runner


@pytest.mark.parametrize("testcase", discover_cocotb_tests(TESTS_DIR / "test_gcd.py"))
def test_gcd(built_gcd, testcase):
    built_gcd.test(
        hdl_toplevel="gcd",
        test_module="test_gcd",
        testcase=testcase,
    )
