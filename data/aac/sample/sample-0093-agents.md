## 2026-02-07 - Package Metadata Export

### Decision/Learning
Expose `__version__` via `from src import *` by declaring `__all__ = ["__version__"]` in `src/__init__.py`.

### Reason
Leading-underscore names are excluded from star imports unless explicitly exported with `__all__`.

### Impact
When adding package-level metadata that must be externally visible, include it in `__all__` and cover with import-surface tests.

## 2026-02-07 - Client Parse Error Test Setup

### Decision/Learning
To exercise the JSON-parse failure branch in `OpenGoKrClient`, malformed JSON must still match `var result = {...};` shape.

### Reason
If the script block does not match the regex first, code raises "Could not find result data" instead of parse failure.

### Impact
For parse-failure tests, keep braces/semicolon intact and break JSON validity inside the object (for example single-quoted keys).

## 2026-02-07 - responses Network Exception Injection

### Decision/Learning
In `responses`, setting `body` to a `requests.exceptions.*` instance raises that exception from the mocked request call.

### Reason
This reliably drives network-error branches without patching internals or adding custom transport code.

### Impact
Prefer this pattern for client/notifier network-failure tests to keep failure setup focused and deterministic.

## 2026-02-07 - Covering `main` Module Entrypoint

### Decision/Learning
Use `runpy.run_module("main", run_name="__main__")` with `pytest.raises(SystemExit)` to cover the `if __name__ == "__main__":` branch.

### Reason
Spawning a subprocess does not contribute to in-process coverage metrics, so line coverage for module entrypoints can remain missing.

### Impact
When targeting script entrypoint coverage, execute the module in-process via `runpy` and assert on the propagated exit code.

## 2026-02-21 - Local Dev Commands

### Decision/Learning
Use `pytest` for tests, `ruff check src tests` for linting, and `mypy src` for type checks. Run the CLI with `open-go-kr` and pass dates via `--dates "YYYY-MM-DD,YYYY-MM-DD"`.

### Reason
These are the documented development and runtime commands in the README.

### Impact
Prefer these commands for local verification and date-scoped runs before pushing changes.