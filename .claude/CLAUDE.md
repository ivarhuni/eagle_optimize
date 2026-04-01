# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Instructions

- This repository is a Python CLI project.
- Prefer simple standard-library solutions unless an external dependency clearly improves reliability.
- Do not commit generated personal reports or profile data (`profiles/`, `optimizations/`).
- The canonical runtime flow is: onboarding updates `profiles/current_profile.*`, `ask` writes a categorized report under `optimizations/`.
- When analyzing user questions, prefer the current profile plus relevant prior notes over generic advice.
- For medication or dosing questions, keep answers documentation-focused and clinician-safe.

## Commands

Install for development:

```bash
uv sync --extra dev
# or
pip install -e ".[dev]"
```

Run all tests:

```bash
uv run --extra dev pytest
```

Run a single test file or test:

```bash
uv run --extra dev pytest tests/test_cli.py
uv run --extra dev pytest tests/test_cli.py::test_cli_without_tty_shows_help_without_banner
```

Run the CLI directly after install:

```bash
eagle-optimize --help
eagle-optimize config init
eagle-optimize doctor
eagle-optimize onboarding run --name baselineProfile
eagle-optimize ask "Is milk good for me?"
eagle-optimize history search "digestive response milk"
```

## Architecture

The CLI is built with Typer and organized into four command groups registered in [cli.py](src/eagle_optimize/cli.py): the root `app`, and sub-typers `config`, `onboarding`, and `history`.

**Request flow for `ask`:**
1. `cli.py` loads the user profile from `profiles/current_profile.md`.
2. `retrieval.py` keyword-scores all markdown files in `profiles/` and `optimizations/` to find related prior notes.
3. `cli.py` dispatches to either `ClaudeCliBackend` ([claude_bridge.py](src/eagle_optimize/claude_bridge.py)) or `CopilotCliBackend` ([copilot_bridge.py](src/eagle_optimize/copilot_bridge.py)).
4. The Claude backend calls the `claude` CLI subprocess with `--json-schema` to enforce a structured JSON response (`RESPONSE_SCHEMA` in `claude_bridge.py`).
5. `reports.py` renders the JSON into a Markdown report; `storage.py` writes it to `optimizations/<category>/`.
6. If Obsidian mirroring is enabled, `storage.mirror_markdown_file` copies the file into the configured vault.

**Module responsibilities:**
- `storage.py` — all file I/O, path helpers, `note_files()`, Obsidian mirror logic, category-folder mapping.
- `config.py` — `AppConfig` dataclass, platform-aware config dir (`~/Library/Application Support/eagle-optimize` on macOS), load/save.
- `retrieval.py` — keyword search over local markdown files, returns scored results with excerpts.
- `reports.py` — Markdown rendering for profiles, assessments, and optimization reports; `guess_category_folder` maps queries to category folders.
- `banner.py` — startup ASCII art library (100 arts), rendered only when stdout is a real TTY.
- `terminal_loader.py` — animated spinner shown while the backend subprocess runs.
- `questionnaire.py` — interactive onboarding prompt collection.

**Config** is stored outside the repo at the platform app-data path (not in `~/.eagle-optimize`). Use `eagle-optimize config show` to find the path.

**Backend selection:** resolved at runtime via `BACKEND_ALIASES` in `cli.py`. The default is `claude-code-cli`; the alternative is `github-copilot-cli`. The active backend is checked with `doctor()` before every `ask` call.

## Project Structure

- `src/eagle_optimize/` — CLI and runtime code.
- `profiles/` — onboarding state (`current_profile.json`, `current_profile.md`) and timestamped assessment snapshots.
- `optimizations/` — categorized Markdown reports (`foodLiquids/`, `drugsSupplements/`, `mentalHeadspace/`, `body/`, `dailyRoutine/`).
- `.claude/skills/` — project-level Claude skills.
- `.claude/agents/` — project-level Claude subagents.
