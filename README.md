# CS527 Research Project: PyIDFix

Automatic detection and repair of implementation-dependent (ID) flaky tests in Python.

**Authors:** Brandon Li, Jenny Chung

---

## Overview

PyIDFix is a Pytest plugin that:

1. **Detects** suspicious patterns (unordered iteration, unseeded randomness, etc.)
2. **Confirms** flakiness via execution under varied environments
3. **Generates** deterministic patches
4. **Validates** that patches eliminate flakiness

---

## Environment Setup

### Prerequisites

- **Python 3.10+** (as specified in the project proposal)
- Recommended: Ubuntu 24.04 for reproducibility

### 1. Create a Virtual Environment

```bash
# From project root
python3 -m venv .venv

# Activate (Unix/macOS)
source .venv/bin/activate

# Activate (Windows)
.venv\Scripts\activate
```

### 2. Install the Package in Editable Mode

```bash
pip install -e .
```

This installs:

- `pytest>=7.0` (required for the plugin)
- The `pyidfix` package as an editable install

### 3. Verify Installation

```bash
# Run unit tests for the tool
pytest tests/ -v

# Verify the plugin is discoverable
pytest --version
pip show pyidfix
```

### Optional: Development Dependencies

```bash
pip install -e ".[dev]"
```

Adds `ruff` for linting.

---

## Project Structure

```
CS527-Research-Project/
├── pyproject.toml       # Package config, dependencies, pytest plugin entry point
├── README.md
├── .gitignore
│
├── pyidfix/            # Main tool (Pytest plugin)
│   ├── __init__.py
│   ├── plugin.py       # Pytest hooks
│   ├── analyzer.py     # Static Pattern Analyzer
│   ├── variant_generator.py
│   ├── patch_generator.py
│   ├── validator.py
│   └── run.py          # Pipeline (analyze → patch → validate)
│
├── eval_dataset/       # Generated test suite for evaluation
│   ├── README.md       # Dataset format, ground truth schema
│   └── programs/       # Individual programs (to be populated)
│
└── tests/              # Unit tests for the tool itself
    └── test_plugin.py
```

---

## Usage

### Programmatic API

```python
from pyidfix.analyzer import analyze_file
from pyidfix.patch_generator import patch_file
from pyidfix.validator import validate_patched_test
from pyidfix.variant_generator import run_test_with_variants, is_flaky

# 1. Analyze a test file for suspicious patterns
findings = analyze_file("tests/test_flaky.py")

# 2. Generate patches
patched_source = patch_file("tests/test_flaky.py", findings)

# 3. Run tests under variants (e.g. different PYTHONHASHSEED)
results = run_test_with_variants("tests/test_flaky.py::test_foo", hash_seeds=[0, 1, 2])
flaky = is_flaky(results)

# 4. Validate patched tests
ok, results = validate_patched_test("tests/test_flaky_patched.py::test_foo")
```

### Run Evaluation Dataset

```bash
# Run all evaluation programs (includes flaky tests)
pytest eval_dataset/programs/ -v

# Run a specific program
pytest eval_dataset/programs/prog_01_dict_iter/tests/ -v
```

### Run Tool Tests

```bash
# Unit tests for each component
pytest tests/test_analyzer.py tests/test_variant_generator.py -v
pytest tests/test_patch_generator.py tests/test_validator.py -v

# Integration tests (full pipeline)
pytest tests/test_integration.py -v

# All tests
pytest tests/ -v
```
