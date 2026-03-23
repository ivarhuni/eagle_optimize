# eagle_optimize

Cross-platform CLI for personal optimization workflows backed by Claude Code.

## Why this stack

CLI tools are usually not written in React. React can power terminal UIs through libraries like Ink, but that is mainly useful when you need a rich interactive terminal interface. For this project, the better first version is:

- Python 3.9+
- Typer for the CLI surface
- Markdown and JSON files for durable local records
- Claude Code CLI as the first AI backend
- Optional Obsidian mirroring for desktop note management

That choice is pragmatic for macOS bash and Windows PowerShell:

- Python runs well in both environments
- subprocess integration with the installed `claude` CLI is straightforward
- local file storage stays human-readable and Claude-friendly
- later packaging to single-file binaries with PyInstaller is realistic

## Claude integration recommendation

The supported first implementation is to call the installed `claude` CLI in print mode.

- This fits a user who already has a Claude subscription and uses Claude Code.
- The app relies on the user's existing Claude Code login state.
- For a future fallback, the architecture is compatible with a direct Anthropic API backend.

Important constraint:

- Anthropic documents the Claude API as API-key based.
- Claude Code documents a logged-in terminal CLI that can also be scripted.
- This repo uses the scripted Claude Code CLI path first.

## What the MVP does

1. Runs a reusable onboarding questionnaire.
2. Stores a current profile plus timestamped assessment snapshots.
3. Lets the user ask optimization questions in plain language.
4. Pulls in relevant past notes before prompting Claude.
5. Prints a short terminal answer.
6. Writes a detailed Markdown report to a categorized folder.
7. Optionally mirrors reports into an Obsidian vault.

## Repository layout

```text
profiles/
	current_profile.json
	current_profile.md
	assessments/
optimizations/
	foodLiquids/
	drugsSupplements/
	mentalHeadspace/
	body/
	dailyRoutine/
```

Generated reports and personal profile data are gitignored by default because they are likely sensitive.

## Categories

Question reports are saved under these camelCase folders:

- `foodLiquids`
- `drugsSupplements`
- `mentalHeadspace`
- `body`
- `dailyRoutine`

## Onboarding coverage

The questionnaire includes your requested fields and a few missing categories that matter in practice:

- age
- sex and gender
- genetic background and ancestry context
- medical limitations and diagnoses
- allergies and intolerances
- current medications
- supplements
- sleep patterns
- physical activity and movement limitations
- routine and work pattern
- digestive responses
- substance use including caffeine, nicotine, alcohol, and cannabis
- stress and mood baseline
- lab findings and clinician guidance
- goals and experiment history

## Safety model

This project is intentionally conservative for higher-risk medical topics.

- It can organize context, prior observations, and follow-up questions.
- It can summarize general considerations and reasoning.
- It should not act like a prescriber.
- For prescription medications, the prompts are written to surface context, flags, and clinician questions rather than provide a direct dosing plan.

## Setup

### 1. Install Claude Code

macOS or Linux:

```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Windows PowerShell:

```powershell
irm https://claude.ai/install.ps1 | iex
```

Then log in:

```bash
claude
```

### 2. Install this project

```bash
uv sync
```

Or with pip:

```bash
python3 -m pip install -e .
```

### 3. Initialize local app config

```bash
eagle-optimize config init
```

That stores local machine config outside the repo and can set:

- the Claude command path
- whether Obsidian mirroring is enabled
- the Obsidian vault path

## Usage

Run onboarding:

```bash
eagle-optimize onboarding run --name baselineProfile
```

Ask a question:

```bash
eagle-optimize ask "Is milk good for me?"
eagle-optimize ask "How should I think about my ADHD medication conversation with my clinician?"
```

Search prior notes:

```bash
eagle-optimize history search "digestive response milk"
```

Inspect Claude connectivity:

```bash
eagle-optimize doctor
```

## Claude Code project support

This repo also includes:

- `.claude/CLAUDE.md` for project-level behavior
- `.claude/skills/optimization-context/SKILL.md` for note-aware analysis
- `.claude/agents/personal-optimization-analyst.md` for direct repo use inside Claude Code

That means your friend can use either:

- the wrapper CLI in this repo
- Claude Code directly inside the repo with the provided project context

## Packaging later

The first version is source-based. When the workflow is stable, the next step is packaging binaries with PyInstaller for:

- macOS terminal use
- Windows PowerShell use

## Tests

```bash
uv run --extra dev pytest
```
