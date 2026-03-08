import json
import subprocess
from pathlib import Path

import pytest
from cocotb_tools.runner import get_runner

TESTS_DIR = Path(__file__).parent
SIM_BUILD = TESTS_DIR / "sim_build"

DEFAULT_SCHEDULE = [
    {
        "g_i": 0.85,
        "g_o": 0.85,
        "until": {"kind": "cycles", "count": 1000},
        "timeout_cycles": 1001,
    },
    {"g_i": 0.0, "g_o": 0.85, "until": {"kind": "drained"}, "timeout_cycles": 2000},
]

ALL_SUBDIRS = [
    "fifo",
    "decoupled",
    "moore",
    "decoupled_array",
    "moore_array",
    "half_stage",
    "half_stage_array",
    "blocked_stage",
    "blocked_stage_array",
]


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


def _test_env(dut_subdir):
    """Return extra_env dict for a runner.test() call."""
    return {
        "COCOTB_SCHEDULE": json.dumps(DEFAULT_SCHEDULE),
        "STATS_PATH": str(SIM_BUILD / dut_subdir / "stats.json"),
    }


# ── Build fixtures ──────────────────────────────────────────────────────────


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


@pytest.fixture(scope="session")
def built_half_stage():
    return _build(
        ["HalfStage.v", "half_stage_wrap.v"],
        "half_stage_wrap",
        SIM_BUILD / "half_stage",
        always=False,
    )


@pytest.fixture(scope="session")
def built_half_stage_array():
    return _build(
        ["HalfStage.v", "half_stage_wrap.v", "half_stage_array.v"],
        "half_stage_array",
        SIM_BUILD / "half_stage_array",
        always=True,
        extra_build_args=["-GN=16"],
    )


@pytest.fixture(scope="session")
def built_blocked_stage():
    return _build(
        ["BlockedStage.v", "blocked_stage_wrap.v"],
        "blocked_stage_wrap",
        SIM_BUILD / "blocked_stage",
        always=False,
    )


@pytest.fixture(scope="session")
def built_blocked_stage_array():
    return _build(
        ["BlockedStage.v", "blocked_stage_wrap.v", "blocked_stage_array.v"],
        "blocked_stage_array",
        SIM_BUILD / "blocked_stage_array",
        always=True,
        extra_build_args=["-GN=16"],
    )


# ── Coverage fixtures ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def capture_coverage(request):
    """Rename coverage.dat after each test so runs don't overwrite each other."""
    yield
    for subdir in (SIM_BUILD / d for d in ALL_SUBDIRS):
        coverage_dat = subdir / "coverage.dat"
        if coverage_dat.exists():
            safe_name = request.node.name.replace("[", "_").replace("]", "")
            coverage_dat.rename(subdir / f"cov_{safe_name}.dat")


@pytest.fixture(scope="session", autouse=True)
def generate_coverage_report():
    """Merge per-test coverage files and produce an annotated report."""
    yield
    for subdir in (SIM_BUILD / d for d in ALL_SUBDIRS):
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


@pytest.fixture(scope="session", autouse=True)
def verify_stats_vs_vcd():
    """After all tests, assert inline HandshakeStats match VCD analysis."""
    yield
    import sys

    sys.path.insert(0, str(TESTS_DIR))
    from analyze_vcd import analyze

    for subdir in (SIM_BUILD / d for d in ALL_SUBDIRS):
        stats_path = subdir / "stats.json"
        vcd_path = subdir / "dump.vcd"
        if not stats_path.exists() or not vcd_path.exists():
            continue
        with open(stats_path) as f:
            inline = json.load(f)
        vcd_data = analyze(vcd_path)
        assert inline["inp_count"] == vcd_data["inp_count"], (
            f"{subdir.name}: inp_count mismatch: "
            f"inline={inline['inp_count']} vcd={vcd_data['inp_count']}"
        )
        assert inline["out_count"] == vcd_data["out_count"], (
            f"{subdir.name}: out_count mismatch: "
            f"inline={inline['out_count']} vcd={vcd_data['out_count']}"
        )
        assert inline["latencies"] == vcd_data["latencies"], (
            f"{subdir.name}: latencies mismatch\n"
            f"  inline[:5]={inline['latencies'][:5]}\n"
            f"  vcd[:5]={vcd_data['latencies'][:5]}"
        )


# ── Test functions ───────────────────────────────────────────────────────────


def test_fifo_random_traffic(built_fifo):
    built_fifo.test(
        hdl_toplevel="fifo",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
        extra_env=_test_env("fifo"),
    )


def test_decoupled_random_traffic(built_decoupled):
    built_decoupled.test(
        hdl_toplevel="decoupled_stage",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
        extra_env=_test_env("decoupled"),
    )


def test_moore_random_traffic(built_moore):
    built_moore.test(
        hdl_toplevel="moore_stage",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
        extra_env=_test_env("moore"),
    )


def test_decoupled_array_random_traffic(built_decoupled_array):
    built_decoupled_array.test(
        hdl_toplevel="decoupled_stage_array",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
        extra_env=_test_env("decoupled_array"),
    )


def test_moore_array_random_traffic(built_moore_array):
    built_moore_array.test(
        hdl_toplevel="moore_stage_array",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
        extra_env=_test_env("moore_array"),
    )


def test_half_stage_random_traffic(built_half_stage):
    built_half_stage.test(
        hdl_toplevel="half_stage_wrap",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
        extra_env=_test_env("half_stage"),
    )


def test_half_stage_array_random_traffic(built_half_stage_array):
    built_half_stage_array.test(
        hdl_toplevel="half_stage_array",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
        extra_env=_test_env("half_stage_array"),
    )


def test_blocked_stage_random_traffic(built_blocked_stage):
    built_blocked_stage.test(
        hdl_toplevel="blocked_stage_wrap",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
        extra_env=_test_env("blocked_stage"),
    )


def test_blocked_stage_array_random_traffic(built_blocked_stage_array):
    built_blocked_stage_array.test(
        hdl_toplevel="blocked_stage_array",
        test_module="test_fifo",
        test_filter="test_random_traffic",
        waves=True,
        extra_env=_test_env("blocked_stage_array"),
    )
