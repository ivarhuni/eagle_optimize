# Project Instructions

- This repository is a Python CLI project.
- Prefer simple standard-library solutions unless an external dependency clearly improves reliability.
- Do not commit generated personal reports or profile data.
- The canonical runtime flow is: onboarding updates `profiles/current_profile.*`, `ask` writes a categorized report under `optimizations/`.
- When analyzing user questions, prefer the current profile plus relevant prior notes over generic advice.
- For medication or dosing questions, keep answers documentation-focused and clinician-safe.

# Project Structure

- `src/eagle_optimize/` contains the CLI and runtime code.
- `profiles/` holds onboarding state and assessments.
- `optimizations/` holds generated categorized reports.
- `.claude/skills/` contains project-level Claude skills.
- `.claude/agents/` contains project-level Claude subagents.