# Evaluation Dataset

Ground-truth dataset for evaluating PyIDFix. Each program contains intentionally
flaky tests with known patterns and documented expected fixes.

## Structure

```
eval_dataset/
├── README.md           # This file
├── programs/           # Individual Python programs with test suites
│   └── prog_XX/        # e.g., prog_01, prog_02, ...
│       ├── src/        # Source modules (optional, or flat)
│       ├── tests/      # pytest test files
│       └── ground_truth.json  # Documented flaky tests and expected fixes
```

## Flakiness Patterns (Ground Truth Categories)

- **unordered_iteration**: dict/set iteration without `sorted()`
- **unseeded_randomness**: `random.*` calls without prior `random.seed()`
- **float_equality**: Exact `==` on floats instead of `pytest.approx()`
- **filesystem_ordering**: `os.listdir()` / `glob` results compared without ordering

## ground_truth.json Format

```json
{
  "program": "prog_01",
  "flaky_tests": [
    {
      "test_id": "tests/test_example.py::test_dict_iteration",
      "pattern": "unordered_iteration",
      "root_cause": "Iterates dict items without sorted(); order varies with PYTHONHASHSEED",
      "expected_fix": "Use sorted(d.items()) or sorted(d.keys())"
    }
  ],
  "deterministic_tests": ["tests/test_example.py::test_basic_math"]
}
```

## Usage

From project root:

```bash
pytest eval_dataset/programs/prog_01/tests/ -v
```

Or run the full dataset:

```bash
pytest eval_dataset/ -v
```
