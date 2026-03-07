import subprocess
from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner

TESTS_DIR = Path(__file__).parent
SIM_BUILD = TESTS_DIR / "sim_build"
BUILD_LOG = SIM_BUILD / "build.log"


def _build(always=True):
    runner = get_runner("verilator")
    BUILD_LOG.parent.mkdir(exist_ok=True)
    runner.build(
        sources=[TESTS_DIR / "fifo.v"],
        hdl_toplevel="fifo",
        build_args=["--timing", "--coverage"],
        build_dir=SIM_BUILD,
        always=always,
        waves=True,
        log_file=BUILD_LOG,
    )
    return runner


def test_build():
    """Build only — run this first to surface Verilog compile errors clearly."""
    try:
        _build(always=True)
    except Exception:
        log = BUILD_LOG.read_text() if BUILD_LOG.exists() else "(no build log)"
        pytest.fail(f"Build failed:\n\n{log}")


@pytest.fixture(scope="session")
def built_fifo():
    return _build(always=False)


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
    subprocess.run(
        [
            "verilator_coverage",
            "--write-info",
            str(SIM_BUILD / "coverage.info"),
            *[str(f) for f in dat_files],
        ],
        check=False,
    )


def _run(runner, test_name, waves=False):
    runner.test(
        hdl_toplevel="fifo",
        test_module="test_fifo",
        test_filter=test_name,
        waves=waves,
    )


def test_fifo_full_throughput(built_fifo):
    _run(built_fifo, "test_full_throughput", waves=True)


def test_fifo_burst_then_drain(built_fifo):
    _run(built_fifo, "test_burst_then_drain", waves=True)


def test_fifo_concurrent(built_fifo):
    _run(built_fifo, "test_concurrent", waves=True)


def test_fifo_slow_consumer(built_fifo):
    _run(built_fifo, "test_slow_consumer", waves=True)


def test_fifo_slow_producer(built_fifo):
    _run(built_fifo, "test_slow_producer", waves=True)


def test_fifo_backpressure(built_fifo):
    _run(built_fifo, "test_backpressure", waves=True)


def test_fifo_random_traffic(built_fifo):
    _run(built_fifo, "test_random_traffic", waves=True)
