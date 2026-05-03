# Evaluation Scripts

This directory contains the three scripts used to evaluate PyIDFix and produce all results, tables, and plots for the research report.

---

## Quick Start

Run these three commands in order from the project root:

```bash
# 1. Evaluate the tool against all 6 programs
python scripts/eval_dataset.py --out eval_results/results.json

# 2. Collect benchmark data (timing + naive rerun comparison)
python scripts/run_benchmarks.py

# 3. Generate all plots and print summary tables
python scripts/plot_results.py
```

Outputs are written to `eval_results/` (gitignored — regenerate locally).

---

## Scripts

### `eval_dataset.py` — Tool Evaluation

Runs PyIDFix's 3-stage pipeline on every program in `eval_dataset/programs/` and records whether each stage succeeded.

**What it does, step by step:**

1. **Stage 1 — Static Detection**: calls `analyze_file()` on each `test_flaky.py` to check whether the static analyzer identifies the labeled flakiness pattern.
2. **Stage 2 — Determinism Check**: runs `test_deterministic.py` with 10 different `PYTHONHASHSEED` values to confirm the reference (already-correct) tests are stable across environments.
3. **Stage 3 — Patch & Validate**: generates a patched copy of `test_flaky.py`, then re-runs it across 10 seeds to confirm flakiness is eliminated.

**Key options:**

| Flag | Default | Description |
|---|---|---|
| `--out PATH` | `eval_results/results.json` | Where to write the results JSON |
| `--seeds N [N ...]` | `0 1 2 3 4 5 6 7 8 9` | Hash seeds used in stages 2 and 3 |
| `--detail` | off | Print a per-test breakdown for each program |

**Example:**
```bash
python scripts/eval_dataset.py --out eval_results/results.json --detail
```

---

### `run_benchmarks.py` — Benchmark Data Collection

For each labeled flaky test, collects three additional measurements not covered by `eval_dataset.py`:

1. **Analysis time** — wall-clock milliseconds to call `analyze_file()` once.
2. **Variant sweep results** — runs the test 10 times with `PYTHONHASHSEED` set to 0–9 (structured, deterministic sweep) and records pass/fail per seed.
3. **Naive rerun results** — runs the test 10 times with `PYTHONHASHSEED` *removed* from the environment, so Python picks a random hash seed each time (simulates the traditional "just rerun" approach).

**Key options:**

| Flag | Default | Description |
|---|---|---|
| `--out PATH` | `eval_results/benchmark_data.json` | Where to write benchmark JSON |
| `--prog NAME` | all programs | Benchmark only a single program |

**Example:**
```bash
python scripts/run_benchmarks.py
python scripts/run_benchmarks.py --prog prog_05_random_choice  # single program
```

**Runtime:** ~1 minute (14 tests × 20 subprocess calls each).

---

### `plot_results.py` — Plots and Tables

Reads `eval_results/results.json` and `eval_results/benchmark_data.json` and produces four PNG plots plus printed summary tables.

```bash
python scripts/plot_results.py
```

Plots are written to `eval_results/plots/`.

---

## Output Files

### `eval_results/results.json`

Top-level structure:

```json
{
  "programs": [ ... ],
  "totals": {
    "stage_1": { "pass": 13, "total": 14 },
    "stage_2": { "pass": 10, "total": 10 },
    "stage_3": { "pass": 13, "total": 14 }
  },
  "elapsed_s": 78.8
}
```

Each entry in `programs` covers one evaluation program:

```json
{
  "program": "prog_01_dict_iter",
  "stage_1": [
    {
      "test_id": "test_flaky.py::test_dict_items_iteration_order",
      "pattern": "unordered_iteration",
      "detected": true,
      "found_patterns": ["unordered_iteration"]
    }
  ],
  "stage_2": [
    {
      "test_id": "test_deterministic.py::test_dict_items_sorted",
      "all_pass": true,
      "is_flaky": false
    }
  ],
  "stage_3": [
    {
      "test_id": "test_flaky.py::test_dict_items_iteration_order",
      "patch_changed": true,
      "validation_ok": true
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `stage_1.detected` | Static analyzer found the labeled pattern in the test |
| `stage_1.found_patterns` | Which patterns were found (may include multiple) |
| `stage_2.all_pass` | Deterministic test passed on all 10 seeds |
| `stage_2.is_flaky` | Deterministic test showed mixed outcomes — would indicate an issue with the reference test |
| `stage_3.patch_changed` | The patch generator modified the source (a patch was applied) |
| `stage_3.validation_ok` | Patched test now passes consistently on all 10 seeds |

---

### `eval_results/benchmark_data.json`

```json
{
  "tests": [
    {
      "program": "prog_01_dict_iter",
      "test_id": "test_dict_items_iteration_order",
      "full_test_path": "/.../tests/test_flaky.py::test_dict_items_iteration_order",
      "pattern": "unordered_iteration",
      "analyze_time_ms": 1.0,
      "variant_results": [
        { "seed": 0, "passed": true },
        { "seed": 1, "passed": false },
        ...
      ],
      "naive_results": [
        { "run": 1, "passed": false },
        { "run": 2, "passed": true },
        ...
      ],
      "variant_failures_in_10": 9,
      "naive_failures_in_10": 9,
      "variant_detected_flaky": true,
      "naive_detected_flaky": true
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `analyze_time_ms` | Wall-clock time (ms) to statically analyze the test file once |
| `variant_results` | Per-seed pass/fail for seeds 0–9 (structured sweep) |
| `naive_results` | Per-run pass/fail for 10 runs with no `PYTHONHASHSEED` set |
| `variant_failures_in_10` | How many of the 10 variant seeds caused a failure |
| `naive_failures_in_10` | How many of the 10 naive reruns caused a failure |
| `variant_detected_flaky` | `true` if variant sweep saw mixed outcomes (some pass, some fail) |
| `naive_detected_flaky` | `true` if naive reruns saw mixed outcomes |

A test is considered **detected as flaky** by a method only when that method observes *both* passing and failing runs — not when all runs pass (pattern unnoticed) and not when all runs fail (looks like a broken test, not a flaky one).

---

## Plots

### RQ1 — `rq1_detection.png`

**Research question:** How effectively can static analysis identify flaky tests compared to running the tests repeatedly?

**Left — Detection Rate by Pattern**

Grouped bars, one group per flakiness pattern. Blue = static analysis, orange = naive reruns (10×).

- *Static analysis* detects a test if `analyze_file()` finds the labeled pattern in the test source.
- *Naive reruns* detects a test if 10 runs with random `PYTHONHASHSEED` show mixed outcomes.

Key observations:
- Static analysis detects 100% of `unordered_iteration` and `float_equality` tests.
- Naive reruns score **0% on float equality** — float comparisons are deterministic on a single machine, so reruns never produce mixed outcomes. Only static analysis can identify these.
- Static analysis misses 1 `unseeded_randomness` test (`test_random_values`) because the `random` call is inside an external helper function (`get_random_values()` in `source.py`), which the analyzer does not trace into.

**Right — Static Analysis Latency per Program**

Bar chart showing average milliseconds to analyze one test file per program. All programs are under 1.5 ms, confirming that static analysis adds negligible overhead compared to executing the tests.

---

### RQ2 — `rq2_confirmation.png`

**Research question:** How does variant-based execution compare to naive reruns in confirming flakiness?

Grouped bars, same layout as RQ1 left. Blue = variant sweep (seeds 0–9), orange = naive reruns (10×). Detection is mixed-outcome detection as defined above.

Key observations:
- Both methods are equally effective on `unordered_iteration` (71%).
- Variant sweep performs *worse* on `unseeded_randomness` (50% vs 75%) — this is expected because `random.choice` / `random.shuffle` depend on Python's `random` module state, not `PYTHONHASHSEED`. Varying the hash seed doesn't change random outcomes; only the fact that no `random.seed()` is set causes variability across runs.
- Both methods score **0% on float equality** — confirming the RQ1 result: runtime methods cannot detect this pattern.
- Variant sweep's advantage over naive reruns is not detection rate but *reproducibility*: it always runs the same 10 seeds, making results deterministic and comparable across machines.

---

### RQ3 — `rq3_repair.png`

**Research question:** What percentage of detected flaky tests can be automatically repaired?

**Left — Repair Outcome by Pattern**

Stacked bars per pattern. Each bar's total height is the number of labeled tests. Segments:
- **Blue** — detected and successfully repaired (patch applied + validated)
- **Orange** — detected but repair or validation failed
- **Grey** — not detected by static analysis

The bold percentage above each bar is the repair rate among detected tests.

All 13 detected tests were successfully repaired (100%). One test (`test_random_values`) was not detected and therefore not patched — shown in grey on the unseeded_randomness bar.

**Right — Overall Pie**

Same data aggregated across all 14 tests: 13 repaired (blue, 93%), 1 not detected (grey, 7%), 0 detected-but-unrepaired.

---

### RQ4 — `rq4_correctness.png`

**Research question:** Do the generated patches preserve test correctness while eliminating flakiness?

**Left — Avg Pass Rate Before vs After Patch**

Grouped bars, one group per pattern. Red = average pass rate across 10 variant seeds *before* patching; blue = average pass rate *after* patching.

| Pattern | Before (avg) | After (avg) |
|---|---|---|
| Unordered Iteration (n=7) | 14% | 100% |
| Unseeded Randomness (n=3) | 13% | 100% |
| Float Equality (n=3) | 67% | 100% |

Float equality's 67% before-patch average reflects that 2 of the 3 tests always pass (100% each — deterministic on one machine) while 1 always fails (0%), giving a 67% mean. All reach 100% after patching. The dashed line at 100% marks the target.

**Right — Deterministic Test Stability**

Shows that all 10 tests in `test_deterministic.py` files (correctly-written reference tests) remained stable — passing all 10 seeds — confirming that applying patches to `test_flaky.py` does not break the broader test suite.
