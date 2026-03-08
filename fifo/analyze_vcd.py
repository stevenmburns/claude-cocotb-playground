"""Analyze FIFO DUT VCD waveforms to compare throughput and latency.

Run after the test suite has produced VCDs:
    python fifo/analyze_vcd.py
"""

import pathlib
import sys

import vcdvcd

REPO_ROOT = pathlib.Path(__file__).parent.parent

DUTS = [
    ("fifo", REPO_ROOT / "fifo/sim_build/fifo/dump.vcd"),
    ("moore×16", REPO_ROOT / "fifo/sim_build/moore_array/dump.vcd"),
]

OUTPUT_PNG = REPO_ROOT / "fifo/analysis.png"


def find_signal(vcd: vcdvcd.VCDVCD, name: str) -> vcdvcd.Signal:
    """Return the signal whose last path component matches *name*.

    Prefers the $rootio scope (top-level IO) when multiple matches exist.
    Raises KeyError if no match is found.
    """
    candidates = [k for k in vcd.references_to_ids if k.split(".")[-1] == name]
    if not candidates:
        raise KeyError(f"Signal '{name}' not found in VCD")
    # Prefer $rootio scope
    rootio = [c for c in candidates if c.startswith("$rootio.")]
    chosen = rootio[0] if rootio else candidates[0]
    return vcd[chosen]


def analyze(vcd_path: pathlib.Path) -> dict:
    """Return throughput and latency data extracted from a single VCD file."""
    vcd = vcdvcd.VCDVCD(str(vcd_path))

    clk = find_signal(vcd, "clk")
    inp_v = find_signal(vcd, "inp_v")
    inp_r = find_signal(vcd, "inp_r")
    out_v = find_signal(vcd, "out_v")
    out_r = find_signal(vcd, "out_r")

    # Collect rising-edge timestamps (0→1 transitions).
    rising_edges = [
        t for (t, v), (_, pv) in zip(clk.tv[1:], clk.tv) if pv == "0" and v == "1"
    ]

    inp_cycles: list[int] = []  # cycle numbers where inp handshake fires
    out_cycles: list[int] = []  # cycle numbers where out handshake fires
    inp_cumulative: list[int] = []
    out_cumulative: list[int] = []

    inp_count = 0
    out_count = 0

    for cycle, t in enumerate(rising_edges):
        # Sample at T-1 (settled combinatorial values driven before the edge).
        t_sample = t - 1
        if inp_v[t_sample] == "1" and inp_r[t_sample] == "1":
            inp_count += 1
            inp_cycles.append(cycle)
        if out_v[t_sample] == "1" and out_r[t_sample] == "1":
            out_count += 1
            out_cycles.append(cycle)
        inp_cumulative.append(inp_count)
        out_cumulative.append(out_count)

    # Pair inp/out events in FIFO order to compute per-transaction latency.
    n_pairs = min(len(inp_cycles), len(out_cycles))
    latencies = [out_cycles[i] - inp_cycles[i] for i in range(n_pairs)]

    return {
        "n_cycles": len(rising_edges),
        "inp_count": inp_count,
        "out_count": out_count,
        "inp_cumulative": inp_cumulative,
        "out_cumulative": out_cumulative,
        "latencies": latencies,
    }


def median(values: list[int]) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def latency_cdf(latencies: list[int]):
    """Return (x, y) arrays for an empirical CDF of latency values."""
    if not latencies:
        return [], []
    s = sorted(latencies)
    n = len(s)
    x = []
    y = []
    for i, v in enumerate(s):
        x.append(v)
        y.append((i + 1) / n)
    return x, y


def main() -> None:
    import matplotlib.pyplot as plt

    missing = [str(path) for _, path in DUTS if not path.exists()]
    if missing:
        print("ERROR: VCD files not found (run the test suite first):")
        for m in missing:
            print(f"  {m}")
        sys.exit(1)

    print("Analyzing VCD files...\n")

    results: list[tuple[str, dict]] = []
    for label, vcd_path in DUTS:
        print(f"  {label}: {vcd_path.relative_to(REPO_ROOT)}")
        data = analyze(vcd_path)
        results.append((label, data))

    print()
    header = f"{'DUT':<14}  {'inp':>6}  {'out':>6}  {'med lat':>8}  {'max lat':>8}"
    print(header)
    print("-" * len(header))
    for label, d in results:
        lats = d["latencies"]
        med = f"{median(lats):.1f}" if lats else "n/a"
        mx = str(max(lats)) if lats else "n/a"
        print(
            f"{label:<14}  {d['inp_count']:>6}  {d['out_count']:>6}  {med:>8}  {mx:>8}"
        )

    # ── Plot ──────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle("FIFO DUT comparison: cumulative throughput", fontsize=13)

    for label, d in results:
        cycles = list(range(d["n_cycles"]))
        (line,) = ax.plot(cycles, d["inp_cumulative"], label=f"{label} inp")
        ax.plot(
            cycles,
            d["out_cumulative"],
            "--",
            color=line.get_color(),
            label=f"{label} out",
        )

    ax.set_xlabel("Simulation cycle")
    ax.set_ylabel("Cumulative accepted transactions")
    ax.set_title("Throughput (solid = inp, dashed = out)")
    ax.legend(fontsize=12, ncol=2)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_PNG, dpi=150)
    print(f"\nSaved plot to {OUTPUT_PNG.relative_to(REPO_ROOT)}")
    plt.show()


if __name__ == "__main__":
    main()
