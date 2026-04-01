---
description: "Use when adding or changing Typer CLI commands, options, argument parsing, command groups, or CLI output. Covers ergonomics, error handling, and command testing."
name: "Typer CLI Surface Practices"
applyTo:
  - "src/eagle_optimize/cli.py"
  - "tests/test_cli.py"
---

# Typer CLI Practices

- Define user-facing commands with clear names and concise help text.
- Use `typer.Argument` and `typer.Option` with explicit help strings for every user input.
- Keep command functions thin: parse input, call domain helpers, print output.
- Prefer predictable, human-readable terminal output (stable labels and ordering).
- Use `typer.secho` for emphasized status output and `typer.echo` for normal output.
- For invalid state or unsupported input, fail fast with `typer.Exit` and actionable messages.
- Keep backend selection and configuration logic centralized rather than duplicated across commands.
- Preserve existing command namespace patterns (`app`, `config`, `onboarding`, `history`) unless intentionally redesigning.
- Add or update `typer.testing.CliRunner` tests whenever command behavior, output, or flags change.
