"""
Generate tables and plots for the four research questions.

Reads:
  eval_results/results.json       (from scripts/eval_dataset.py)
  eval_results/benchmark_data.json (from scripts/run_benchmarks.py)

Outputs to eval_results/plots/:
  rq1_detection.png   - Static analysis vs naive rerun detection rate + analysis time
  rq2_confirmation.png - Scatter: variant failures vs naive failures per test
  rq3_repair.png      - Repair rate by pattern
  rq4_correctness.png - Pre-patch vs post-patch pass rate aggregated by pattern

Also prints summary tables to stdout.

Usage:
    python scripts/plot_results.py
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = ROOT / "eval_results" / "results.json"
BENCH_PATH = ROOT / "eval_results" / "benchmark_data.json"
PLOTS_DIR = ROOT / "eval_results" / "plots"

PATTERN_LABELS = {
    "unordered_iteration": "Unordered\nIteration",
    "unseeded_randomness": "Unseeded\nRandomness",
    "float_equality": "Float\nEquality",
}
PATTERN_ORDER = ["unordered_iteration", "unseeded_randomness", "float_equality"]

PAT_COLORS = {
    "unordered_iteration": "#4C72B0",
    "unseeded_randomness": "#DD8452",
    "float_equality": "#55A868",
}

COLORS = {
    "static": "#4C72B0",
    "naive": "#DD8452",
    "repaired": "#3498db",
    "det_no_rep": "#e67e22",
    "undetected": "#bdc3c7",
    "before": "#DD8452",
    "after": "#2ecc71",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Missing: {path}\nRun the required script first.")
    return json.loads(path.read_text())


def savefig(fig: plt.Figure, name: str) -> None:
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    out = PLOTS_DIR / name
    fig.savefig(out, dpi=150, bbox_inches="tight")
    print(f"  Saved: {out}")
    plt.close(fig)


def short_name(test_id: str) -> str:
    return test_id.replace("test_", "").replace("_", " ")


# ── RQ1: Static Analysis vs Naive Reruns ──────────────────────────────────────

def plot_rq1(bench: dict, results: dict) -> None:
    """
    RQ1 – Left:  detection rate (%) by pattern for static analysis vs naive reruns
          Right: per-program analysis latency (ms, bar chart)
    """
    tests = bench["tests"]

    # Aggregate per-pattern detection counts
    pattern_stats: dict[str, dict] = {p: {"total": 0, "static": 0, "naive": 0}
                                       for p in PATTERN_ORDER}
    naive_map = {t["test_id"]: t["naive_detected_flaky"] for t in tests}

    for prog in results["programs"]:
        for s1 in prog["stage_1"]:
            p = s1["pattern"]
            if p not in pattern_stats:
                continue
            pattern_stats[p]["total"] += 1
            if s1["detected"]:
                pattern_stats[p]["static"] += 1
            tid = s1["test_id"].split("::")[-1]
            if naive_map.get(tid, False):
                pattern_stats[p]["naive"] += 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("RQ1 — Static Analysis vs. Naive Reruns", fontsize=13, fontweight="bold")

    # ── Left: detection rate by pattern ──────────────────────────────────────
    x = np.arange(len(PATTERN_ORDER))
    w = 0.35
    static_rates = [
        100 * pattern_stats[p]["static"] / pattern_stats[p]["total"]
        if pattern_stats[p]["total"] else 0
        for p in PATTERN_ORDER
    ]
    naive_rates = [
        100 * pattern_stats[p]["naive"] / pattern_stats[p]["total"]
        if pattern_stats[p]["total"] else 0
        for p in PATTERN_ORDER
    ]

    bars1 = ax1.bar(x - w / 2, static_rates, w, label="Static Analysis",
                    color=COLORS["static"], zorder=3)
    bars2 = ax1.bar(x + w / 2, naive_rates, w, label="Naive Reruns (10×)",
                    color=COLORS["naive"], zorder=3)

    for bar in bars1:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                 f"{h:.0f}%", ha="center", va="bottom", fontsize=9)
    for bar in bars2:
        h = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                 f"{h:.0f}%", ha="center", va="bottom", fontsize=9)

    ax1.set_xticks(x)
    ax1.set_xticklabels([PATTERN_LABELS[p] for p in PATTERN_ORDER], fontsize=9)
    ax1.set_ylabel("Detection Rate (%)")
    ax1.set_ylim(0, 140)   # extra headroom so legend sits in top-right clear of bars
    ax1.set_title("Detection Rate by Pattern")
    ax1.legend(fontsize=9, loc="upper right")
    ax1.grid(axis="y", alpha=0.4, zorder=0)
    ax1.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)

    # ── Right: analysis latency per program ───────────────────────────────────
    programs: dict[str, list[float]] = {}
    for t in tests:
        programs.setdefault(t["program"], []).append(t["analyze_time_ms"])
    prog_names = sorted(programs.keys())
    avg_times = [np.mean(programs[p]) for p in prog_names]
    short_names = [p.replace("prog_0", "P").replace("_", "\n") for p in prog_names]

    bars = ax2.bar(range(len(prog_names)), avg_times, color=COLORS["static"], zorder=3)
    max_t = max(avg_times)
    for i, v in enumerate(avg_times):
        ax2.text(i, v + max_t * 0.02, f"{v:.1f}", ha="center", va="bottom", fontsize=8)
    ax2.set_xticks(range(len(prog_names)))
    ax2.set_xticklabels(short_names, fontsize=8)
    ax2.set_ylabel("Analysis Time (ms)")
    ax2.set_ylim(0, max_t * 1.25)
    ax2.set_title("Static Analysis Latency per Program")
    ax2.grid(axis="y", alpha=0.4, zorder=0)

    fig.tight_layout()
    savefig(fig, "rq1_detection.png")

    # Print table
    print("\n── RQ1 Table: Detection Rate by Pattern ──")
    print(f"{'Pattern':<26} {'Total':>6} {'Static':>8} {'Static%':>9} {'Naive':>7} {'Naive%':>8}")
    print("-" * 67)
    for p in PATTERN_ORDER:
        s = pattern_stats[p]
        sp = 100 * s["static"] / s["total"] if s["total"] else 0
        np_ = 100 * s["naive"] / s["total"] if s["total"] else 0
        print(f"{p:<26} {s['total']:>6} {s['static']:>8} {sp:>8.0f}% {s['naive']:>7} {np_:>7.0f}%")

    print("\n── RQ1 Table: Analysis Latency ──")
    print(f"{'Program':<28} {'Avg ms':>8} {'Min ms':>8} {'Max ms':>8}")
    print("-" * 56)
    for prog in sorted(programs.keys()):
        ts = programs[prog]
        print(f"{prog:<28} {np.mean(ts):>8.2f} {min(ts):>8.2f} {max(ts):>8.2f}")


# ── RQ2: Variant Sweep vs Naive Reruns ────────────────────────────────────────

def plot_rq2(bench: dict) -> None:
    """
    RQ2 – Grouped bar chart: flaky-detection rate (%) by pattern,
          comparing variant sweep (seeds 0-9) vs naive reruns (10 random runs).
          A test counts as "detected" when runs show mixed outcomes (some pass, some fail).
    """
    tests = bench["tests"]

    pat_stats: dict[str, dict] = {
        p: {"total": 0, "variant": 0, "naive": 0} for p in PATTERN_ORDER
    }
    for t in tests:
        p = t["pattern"]
        if p not in pat_stats:
            continue
        pat_stats[p]["total"] += 1
        if t["variant_detected_flaky"]:
            pat_stats[p]["variant"] += 1
        if t["naive_detected_flaky"]:
            pat_stats[p]["naive"] += 1

    x = np.arange(len(PATTERN_ORDER))
    w = 0.35
    variant_rates = [
        100 * pat_stats[p]["variant"] / pat_stats[p]["total"] if pat_stats[p]["total"] else 0
        for p in PATTERN_ORDER
    ]
    naive_rates = [
        100 * pat_stats[p]["naive"] / pat_stats[p]["total"] if pat_stats[p]["total"] else 0
        for p in PATTERN_ORDER
    ]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.suptitle("RQ2 — Flaky-Test Detection Rate: Variant Sweep vs. Naive Reruns",
                 fontsize=12, fontweight="bold")

    bars_v = ax.bar(x - w / 2, variant_rates, w,
                    label="Variant Sweep (seeds 0–9)", color=COLORS["static"], zorder=3)
    bars_n = ax.bar(x + w / 2, naive_rates, w,
                    label="Naive Reruns (10×)", color=COLORS["naive"], zorder=3)

    for bar in bars_v:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                f"{h:.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    for bar in bars_n:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width() / 2, h + 0.5,
                f"{h:.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels(
        [f"{PATTERN_LABELS[p]}\n(n={pat_stats[p]['total']})" for p in PATTERN_ORDER],
        fontsize=9,
    )
    ax.set_ylim(0, 140)
    ax.set_title(
        "A test is 'detected' if runs show mixed pass/fail outcomes\n"
        "(float equality is deterministic — neither method detects it via reruns)",
        fontsize=8.5,
    )
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(axis="y", alpha=0.4, zorder=0)

    fig.tight_layout()
    savefig(fig, "rq2_confirmation.png")

    # Print table
    print("\n── RQ2 Table: Variant Sweep vs Naive Reruns ──")
    print(f"{'Test':<38} {'Pattern':<24} {'Variant/10':>10} {'Naive/10':>9} {'V-detect':>9} {'N-detect':>9}")
    print("-" * 102)
    for t in tests:
        print(
            f"{short_name(t['test_id']):<38} {t['pattern']:<24} "
            f"{t['variant_failures_in_10']:>10} {t['naive_failures_in_10']:>9} "
            f"{'Yes' if t['variant_detected_flaky'] else 'No':>9} "
            f"{'Yes' if t['naive_detected_flaky'] else 'No':>9}"
        )


# ── RQ3: Repair Rate ───────────────────────────────────────────────────────────

def plot_rq3(results: dict) -> None:
    """
    RQ3 – Stacked bar chart per pattern (repaired / detected-not-repaired / undetected)
         + overall pie chart.
    Uses blue-orange palette instead of green-red.
    """
    pattern_counts: dict[str, dict] = {
        p: {"repaired": 0, "detected_not_repaired": 0, "undetected": 0}
        for p in PATTERN_ORDER
    }

    for prog in results["programs"]:
        s1_map = {r["test_id"].split("::")[-1]: r for r in prog["stage_1"]}
        s3_map = {r["test_id"].split("::")[-1]: r for r in prog["stage_3"]}

        for test_id, s1 in s1_map.items():
            p = s1["pattern"]
            if p not in pattern_counts:
                continue
            s3 = s3_map.get(test_id)
            if not s1["detected"]:
                pattern_counts[p]["undetected"] += 1
            elif s3 and s3["validation_ok"]:
                pattern_counts[p]["repaired"] += 1
            else:
                pattern_counts[p]["detected_not_repaired"] += 1

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("RQ3 — Automated Repair Rate", fontsize=13, fontweight="bold")

    x = np.arange(len(PATTERN_ORDER))
    rep     = [pattern_counts[p]["repaired"]             for p in PATTERN_ORDER]
    det_nr  = [pattern_counts[p]["detected_not_repaired"] for p in PATTERN_ORDER]
    undet   = [pattern_counts[p]["undetected"]            for p in PATTERN_ORDER]

    ax1.bar(x, rep,    label="Detected & Repaired",     color=COLORS["repaired"],   zorder=3)
    ax1.bar(x, det_nr, bottom=rep, label="Detected, Not Repaired",
            color=COLORS["det_no_rep"], zorder=3)
    ax1.bar(x, undet,  bottom=[r + d for r, d in zip(rep, det_nr)],
            label="Not Detected", color=COLORS["undetected"], zorder=3)

    totals = [r + d + u for r, d, u in zip(rep, det_nr, undet)]
    for i, (r, t) in enumerate(zip(rep, totals)):
        rate = 100 * r / t if t else 0
        ax1.text(i, t + 0.1, f"{rate:.0f}%", ha="center", va="bottom",
                 fontsize=10, fontweight="bold")

    ax1.set_xticks(x)
    ax1.set_xticklabels([PATTERN_LABELS[p] for p in PATTERN_ORDER], fontsize=9)
    ax1.set_ylabel("Number of Tests")
    ax1.set_ylim(0, max(totals) + 2)
    ax1.set_title("Repair Outcome by Pattern")
    ax1.legend(fontsize=8, loc="upper right")
    ax1.grid(axis="y", alpha=0.4, zorder=0)

    # Pie chart — overall breakdown
    total_rep    = sum(rep)
    total_det_nr = sum(det_nr)
    total_undet  = sum(undet)
    sizes   = [total_rep, total_det_nr, total_undet]
    pie_labels = [
        f"Repaired ({total_rep})",
        f"Detected, not repaired ({total_det_nr})",
        f"Not detected ({total_undet})",
    ]
    colors_pie = [COLORS["repaired"], COLORS["det_no_rep"], COLORS["undetected"]]
    non_zero = [(s, l, c) for s, l, c in zip(sizes, pie_labels, colors_pie) if s > 0]
    if non_zero:
        s_nz, l_nz, c_nz = zip(*non_zero)
        ax2.pie(s_nz, labels=l_nz, colors=c_nz,
                autopct="%1.0f%%", startangle=90,
                textprops={"fontsize": 8})
    ax2.set_title("Overall Repair Breakdown")

    fig.tight_layout()
    savefig(fig, "rq3_repair.png")

    # Print table
    total_labeled  = sum(totals)
    total_detected = sum(rep) + sum(det_nr)
    total_repaired = sum(rep)
    print("\n── RQ3 Table: Repair Rate by Pattern ──")
    print(f"{'Pattern':<26} {'Labeled':>8} {'Detected':>9} {'Repaired':>9} {'Repair%':>8}")
    print("-" * 64)
    for p in PATTERN_ORDER:
        c = pattern_counts[p]
        t = c["repaired"] + c["detected_not_repaired"] + c["undetected"]
        det = c["repaired"] + c["detected_not_repaired"]
        rate = 100 * c["repaired"] / det if det else 0
        print(f"{p:<26} {t:>8} {det:>9} {c['repaired']:>9} {rate:>7.0f}%")
    print("-" * 64)
    overall_rate = 100 * total_repaired / total_detected if total_detected else 0
    print(f"{'TOTAL':<26} {total_labeled:>8} {total_detected:>9} {total_repaired:>9} {overall_rate:>7.0f}%")


# ── RQ4: Patch Correctness ────────────────────────────────────────────────────

def plot_rq4(results: dict, bench: dict) -> None:
    """
    RQ4 – Left:  Grouped bar chart aggregated by pattern (avg before/after pass rate).
                 Simpler than one bar per test; still shows all information.
          Right: Deterministic test stability (Stage 2).
    """
    before_map: dict[str, float] = {}
    for t in bench["tests"]:
        passes = sum(1 for r in t["variant_results"] if r["passed"])
        before_map[t["test_id"]] = 100 * passes / len(t["variant_results"])

    # Aggregate before/after by pattern
    pat_before: dict[str, list[float]] = {p: [] for p in PATTERN_ORDER}
    pat_after:  dict[str, list[float]] = {p: [] for p in PATTERN_ORDER}

    for prog in results["programs"]:
        s3_map = {r["test_id"].split("::")[-1]: r for r in prog["stage_3"]}
        s1_map = {r["test_id"].split("::")[-1]: r for r in prog["stage_1"]}
        for test_id, s3 in s3_map.items():
            if not s3["patch_changed"]:
                continue
            pattern = s1_map.get(test_id, {}).get("pattern", "unknown")
            if pattern not in pat_before:
                continue
            before = before_map.get(test_id, 0.0)
            after  = 100.0 if s3["validation_ok"] else 0.0
            pat_before[pattern].append(before)
            pat_after[pattern].append(after)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.8))
    fig.suptitle("RQ4 — Patch Correctness: Pass Rate Before vs After",
                 fontsize=13, fontweight="bold")

    # ── Left: grouped bars by pattern ────────────────────────────────────────
    x = np.arange(len(PATTERN_ORDER))
    w = 0.35
    avg_before = [np.mean(pat_before[p]) if pat_before[p] else 0 for p in PATTERN_ORDER]
    avg_after  = [np.mean(pat_after[p])  if pat_after[p]  else 0 for p in PATTERN_ORDER]
    n_tests    = [len(pat_before[p]) for p in PATTERN_ORDER]

    bars_b = ax1.bar(x - w / 2, avg_before, w, label="Before patch",
                     color="#C44E52", zorder=3)
    bars_a = ax1.bar(x + w / 2, avg_after,  w, label="After patch",
                     color="#4C72B0", zorder=3)

    for bar, val in zip(bars_b, avg_before):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + 1,
                 f"{val:.0f}%", ha="center", va="bottom", fontsize=9)
    for bar, val in zip(bars_a, avg_after):
        ax1.text(bar.get_x() + bar.get_width() / 2, val + 1,
                 f"{val:.0f}%", ha="center", va="bottom", fontsize=9)

    ax1.set_xticks(x)
    labels_with_n = [f"{PATTERN_LABELS[p]}\n(n={n_tests[i]})"
                     for i, p in enumerate(PATTERN_ORDER)]
    ax1.set_xticklabels(labels_with_n, fontsize=8.5)
    ax1.set_ylabel("Seeds Passing (%, avg of 10)")
    ax1.set_ylim(0, 140)
    ax1.axhline(100, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
    ax1.set_title("Avg Pass Rate Before vs After Patch")
    ax1.legend(fontsize=9, loc="upper right")
    ax1.grid(axis="y", alpha=0.4, zorder=0)

    # ── Right: deterministic test stability ───────────────────────────────────
    stable    = sum(1 for prog in results["programs"]
                    for r in prog["stage_2"] if r["all_pass"] and not r["is_flaky"])
    total_det = sum(len(prog["stage_2"]) for prog in results["programs"])

    ax2.bar(["Stable\n(all seeds pass)", "Unstable"],
            [stable, total_det - stable],
            color=["#4C72B0", "#bdc3c7"], zorder=3)
    ax2.set_ylabel("Number of Deterministic Tests")
    ax2.set_title(f"Deterministic Test Stability\n(Stage 2 — {total_det} tests, 10 seeds each)")
    ax2.set_ylim(0, total_det + 2)
    ax2.text(0, stable + 0.2, f"{stable}/{total_det}\n({100*stable/total_det:.0f}%)",
             ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax2.grid(axis="y", alpha=0.4, zorder=0)

    fig.tight_layout()
    savefig(fig, "rq4_correctness.png")

    # Print table
    print("\n── RQ4 Table: Pre/Post Patch Pass Rate by Pattern ──")
    print(f"{'Pattern':<26} {'N tests':>8} {'Avg Before%':>12} {'Avg After%':>11}")
    print("-" * 60)
    for p in PATTERN_ORDER:
        nb = np.mean(pat_before[p]) if pat_before[p] else 0
        na = np.mean(pat_after[p])  if pat_after[p]  else 0
        n  = len(pat_before[p])
        print(f"{p:<26} {n:>8} {nb:>11.0f}% {na:>10.0f}%")
    print(f"\n  Deterministic tests stable: {stable}/{total_det} "
          f"({100*stable/total_det:.0f}%)")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("Loading data...")
    results = load_json(RESULTS_PATH)
    bench   = load_json(BENCH_PATH)

    print("\n=== RQ1: Static Analysis vs Naive Reruns ===")
    plot_rq1(bench, results)

    print("\n=== RQ2: Variant Sweep vs Naive Reruns ===")
    plot_rq2(bench)

    print("\n=== RQ3: Repair Rate ===")
    plot_rq3(results)

    print("\n=== RQ4: Patch Correctness ===")
    plot_rq4(results, bench)

    print(f"\nAll plots saved to {PLOTS_DIR}/")


if __name__ == "__main__":
    main()
