from pathlib import Path
from cocotb_tools.runner import get_runner

TESTS_DIR = Path(__file__).parent


def test_gcd():
    runner = get_runner("verilator")
    runner.build(
        sources=[TESTS_DIR / "gcd.v"],
        hdl_toplevel="gcd",
        build_args=["--timing"],
        always=True,
    )
    runner.test(
        hdl_toplevel="gcd",
        test_module="test_gcd",
    )
