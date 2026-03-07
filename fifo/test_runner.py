import subprocess
from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner

TESTS_DIR = Path(__file__).parent
SIM_BUILD = TESTS_DIR / "sim_build"


def _build(sources, toplevel, sim_build, always=True, extra_build_args=None):
    runner = get_runner("verilator")
    if sim_build.exists() and not sim_build.is_dir():
        sim_build.unlink()
    sim_build.mkdir(parents=True, exist_ok=True)
    build_log = sim_build / "build.log"
    build_args = ["--timing", "--coverage"] + (extra_build_args or [])
    runner.build(
        sources=[TESTS_DIR / s for s in sources],
        hdl_toplevel=toplevel,
        build_args=build_args,
        build_dir=sim_build,
        always=always,
        waves=True,
        log_file=build_log,
    )
    return runner


@pytest.fixture(scope="session")
def built_fifo():
    return _build(["fifo.v"], "fifo", SIM_BUILD / "fifo", always=False)


@pytest.fixture(scope="session")
def built_decoupled():
    return _build(
        ["decoupled_stage.v"], "decoupled_stage", SIM_BUILD / "decoupled", always=False
    )


@pytest.fixture(scope="session")
def built_moore():
    return _build(["moore_stage.v"], "moore_stage", SIM_BUILD / "moore", always=False)


@pytest.fixture(scope="session")
def built_decoupled_array():
    return _build(
        ["decoupled_stage.v", "decoupled_stage_array.v"],
        "decoupled_stage_array",
        SIM_BUILD / "decoupled_array",
        always=True,
        extra_build_args=["-GN=16"],
    )


@pytest.fixture(scope="session")
def built_moore_array():
    return _build(
        ["moore_stage.v", "moore_stage_array.v"],
        "moore_stage_array",
        SIM_BUILD / "moore_array",
        always=True,
        extra_build_args=["-GN=16"],
    )


@pytest.fixture(autouse=True)
def capture_coverage(request):
    """Rename coverage.dat after each test so runs don't overwrite each other."""
    yield
    for subdir in (
        SIM_BUILD / "fifo",
        SIM_BUILD / "decoupled",
        SIM_BUILD / "moore",
        SIM_BUILD / "decoupled_array",
        SIM_BUILD / "moore_array",
    ):
        coverage_dat = subdir / "coverage.dat"
        if coverage_dat.exists():
            safe_name = request.node.name.replace("[", "_").replace("]", "")
            coverage_dat.rename(subdir / f"cov_{safe_name}.dat")


@pytest.fixture(scope="session", autouse=True)
def generate_coverage_report():
    """Merge per-test coverage files and produce an annotated report."""
    yield
    for subdir in (
        SIM_BUILD / "fifo",
        SIM_BUILD / "decoupled",
        SIM_BUILD / "moore",
        SIM_BUILD / "decoupled_array",
        SIM_BUILD / "moore_array",
    ):
        if not subdir.exists():
            continue
        dat_files = sorted(subdir.glob("cov_*.dat"))
        if not dat_files:
            continue
        annotated = subdir / "coverage_annotated"
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
                str(subdir / "coverage.info"),
                *[str(f) for f in dat_files],
            ],
            check=False,
        )


def test_fifo_random_traffic(built_fifo):
    built_fifo.test(
        hdl_toplevel="fifo",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
    )


def test_decoupled_random_traffic(built_decoupled):
    built_decoupled.test(
        hdl_toplevel="decoupled_stage",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
    )


def test_moore_random_traffic(built_moore):
    built_moore.test(
        hdl_toplevel="moore_stage",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
    )


def test_decoupled_array_random_traffic(built_decoupled_array):
    built_decoupled_array.test(
        hdl_toplevel="decoupled_stage_array",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
    )


def test_moore_array_random_traffic(built_moore_array):
    built_moore_array.test(
        hdl_toplevel="moore_stage_array",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
    )
