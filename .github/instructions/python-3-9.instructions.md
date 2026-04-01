---
description: "Use when writing or modifying Python code in this repository. Enforces Python 3.9+ compatibility, typing, pathlib-first file handling, and test updates."
name: "Python 3.9+ Repository Practices"
applyTo:
  - "src/**/*.py"
  - "tests/**/*.py"
---

# Python 3.9+ Practices

- Keep code compatible with Python 3.9+.
- Do not use Python 3.10+ only syntax (for example, `X | Y` union types or `match` statements).
- Add type hints for all new or modified public functions and command handlers.
- Prefer `from __future__ import annotations` in modules that add or expand type annotations.
- Use `pathlib.Path` for filesystem paths and path composition.
- Read and write text files with explicit UTF-8 encoding.
- Keep functions focused and side effects isolated to the CLI boundary.
- Raise explicit, user-meaningful errors rather than silently returning fallback values.
- When behavior changes, add or update pytest coverage in `tests/` in the same change.
