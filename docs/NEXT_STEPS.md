# PyIDFix: Roadmap and Evaluation

---

## 1. Demo: showing one test through the pipeline (recommended centerpiece)

This is a method to prove the tool works: pick **one** pytest node id (e.g. a flaky test in `eval_dataset`), run a **single command**, and get a **fixed, readable narrative** of every stage plus proof the flakiness is gone.

### 1.1 What the audience should see (storyline)

1. **Analyze** — “We scanned the test file and found: pattern X at line L in `test_foo`.”
2. **Confirm (optional but strong)** — “We ran the same test with 10 different `PYTHONHASHSEED` values: pass/fail grid → _flaky_ (mixed outcomes) or _stable failure_ with varying output.”
3. **Patch** — “We applied a rule-based fix.” Show a **unified diff** (only the changed lines), not the whole file.
4. **Validate** — “We re-ran the **patched** test under the same seeds: all pass, outcomes consistent.”

That sequence matches the paper’s pipeline and is easy to screenshot or narrate.

### 1.2 Implementation outline (what to build)

**Entry point:** `python -m pyidfix demo <path/to/test_file.py::test_name>` (or `pyidfix pipeline …`). Keep it **separate from** `pytest`’s normal output so the demo is not buried under pytest’s own logs.

**Behavior:**

1. Resolve paths and `cwd` the same way `variant_generator` already does for `eval_dataset` programs.
2. **Stage A — Analyze:** Call `analyze_file` on the test file. Filter findings to those whose `function_name` matches the selected test (if a specific `::test` was given). Print a small table or bullet list: `pattern`, `line`, `message`.
3. **Stage B — Variants (before patch):** Call `run_test_with_variants(test_path, hash_seeds=[0..9])`. Print one line per seed: `hashseed_k → PASS/FAIL`. Print `is_flaky(results)` in plain language (“Outcomes differ across seeds → likely ID flakiness” / “All same → not flaky by this check”).
4. **Stage C — Patch:** Call `generate_patch` with the **same file’s** findings (optionally only findings for that test function). Compute a **unified diff** against the original (stdlib `difflib.unified_diff` is enough). Print the diff. Optionally write the patched source to a **temp file** next to the original or under `/tmp` with a predictable name for inspection.
5. **Stage D — Validate:** Point `validate_patched_test` at the **temp file** + same `::test_name`. Print the same pass/fail grid; success = all PASS and not flaky.

**Verbosity (avoid clutter):**

| Flag                   | Behavior                                                                     |
| ---------------------- | ---------------------------------------------------------------------------- |
| _(default)_            | Stages 1–4 with short summaries + full diff (diff is usually small).         |
| `-q`                   | Only final summary: “flaky before: yes/no”, “validate after patch: OK/FAIL”. |
| `-v`                   | Include truncated pytest stdout for failed variant runs (first N lines).     |
| `--json-out path.json` | Machine-readable record of all four stages for slides / reproducibility.     |

**Large vs small in the same tool:**

- **Demo live:** run `demo` on **one** `eval_dataset` test (small, fast, understandable).
- **Batch credibility:** keep **`scripts/eval_dataset.py`** (see §2) for many programs; output a **summary table** only, not 50 diffs. Optionally run `demo --json-out` once per flaky test overnight into `eval_results/`.

### 1.3 What to add or drop for the demo

| Include                        | Why                                                       |
| ------------------------------ | --------------------------------------------------------- |
| `demo` / `pipeline` CLI above  | Single command tells the whole story.                     |
| Unified diff                   | Shows the fix is real code, not a black box.              |
| Optional `--json-out`          | Easy to paste into report or slides.                      |
| `eval_dataset.py` batch script | Proves scale across many programs without live-scrolling. |

| Skip (for this course demo)                     | Why                                                         |
| ----------------------------------------------- | ----------------------------------------------------------- |
| `pytest --pyidfix`                              | Nice-to-have; same behavior as CLI with more pytest wiring. |
| Printing full subprocess pytest logs by default | Too noisy; hide behind `-v`.                                |

### 1.4 Evaluation script (batch verification)

- **`scripts/eval_dataset.py`:** For each `eval_dataset/programs/*/ground_truth.json`, run Level A / B / C checks (see §4) and write **`results.json`** plus a one-line **summary** (e.g. `7/8 validate OK`).
- Optional: internally call the same code paths as `pyidfix demo` so behavior stays consistent.

**Out of scope for this project doc:** timestamp/filesystem flakiness, deep pytest hooks, mining large open-source repos, LLM grading of patches.

---

## 2. LLM-generated programs (10–15)

### 2.1 Contents of each program

1. Small module(s) under `eval_dataset/programs/prog_XX/`.
2. `tests/` + `conftest.py` (path setup—mirror `prog_01`–`prog_03`).
3. **Deterministic** tests (stable under variant runs) and **intentionally flaky** tests using only:
   - unordered dict/set iteration,
   - unseeded `random.*`,
   - `assert x == <float literal>` without `pytest.approx`.
4. **`ground_truth.json`** with `test_id`, `pattern`, `root_cause`, `expected_fix` for each flaky test.

### 2.2 LLM prompt checklist

- Layout from `eval_dataset/README.md`.
- **pytest only**, no extra dependencies.
- Deterministic tests must remain passing when flaky neighbors are patched (isolate flaky tests in separate functions/files if needed).

---

## 3. Pytest and PyIDFix (description in demo)

- **Normal workflow:** Developers run **`pytest`** on their project as usual.
- **PyIDFix** is used **alongside** pytest: it **analyzes** test source, **re-runs** specific tests via **`python -m pytest` in subprocesses** with different `PYTHONHASHSEED` values, **patches** the source, and **validates** by subprocess pytest again.
- The installed package registers a **minimal pytest plugin** (marker `pyidfix` only). That does **not** change how tests are collected or executed when you run `pytest`; it is optional metadata for the future.

For the demo and report, it is accurate to say: **“We combine PyIDFix with pytest: pytest executes tests; our tool drives pytest in controlled environments to find and fix implementation-dependent flakiness.”**

---

## 4. Verifiable outcomes (demo / batch)

### Level A — Detection

For each `(test_id, pattern)` in `ground_truth.json` → `flaky_tests`, the analyzer produces at least one `Finding` with that `pattern` for the function named in `test_id`.

### Level B — Deterministic tests stable

For each `deterministic_tests` entry, `run_test_with_variants` (e.g. seeds 0–9): all runs pass and `is_flaky` is false.

### Level C — Repair

After `patch_file` and writing a patched copy, `validate_patched_test` on the flaky `test_id` returns `(True, ...)`.

Store runs under `eval_results/<run_id>/` (e.g. `results.json` + optional `demo_*.json` from the CLI).

---

## 5. Division of labor

| Who          | Focus                                                                                              |
| ------------ | -------------------------------------------------------------------------------------------------- |
| **Partner**  | 10–15 programs + `ground_truth.json`; run batch script; note failures.                             |
| **Tool dev** | Implement **`pyidfix demo`** (§1) + **`scripts/eval_dataset.py`**; keep `prog_01`–`prog_03` green. |

---

## 6. Order of work

1. Implement **`python -m pyidfix demo`** (or equivalent) with default + `--json-out` + optional `-q` / `-v`.
2. Implement **`scripts/eval_dataset.py`**; achieve full pass on `prog_01`–`prog_03` for Levels A–C.
3. Add LLM programs in batches; fix tool only when the batch script fails consistently.
4. **Live demo:** run `demo` on one flaky test → scroll the four stages → show `results.json` summary for the full eval set.
