from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional

import typer

from eagle_optimize.claude_bridge import BackendError, ClaudeCliBackend
from eagle_optimize.config import load_config, save_config
from eagle_optimize.questionnaire import collect_onboarding_answers
from eagle_optimize.reports import (
    guess_category_folder,
    render_assessment_markdown,
    render_current_profile_markdown,
    render_optimization_report,
)
from eagle_optimize.retrieval import render_context_bundle, search_notes
from eagle_optimize.storage import (
    assessment_paths,
    camel_case_slug,
    current_profile_json_path,
    current_profile_markdown_path,
    ensure_repo_layout,
    latest_assessment_markdown,
    load_json,
    mirror_markdown_file,
    now_timestamp,
    optimization_report_path,
    repo_relative_path,
    write_json,
    write_text,
)


app = typer.Typer(help="Personal optimization CLI backed by Claude Code.")
config_app = typer.Typer(help="Local machine configuration.")
onboarding_app = typer.Typer(help="Onboarding and profile management.")
history_app = typer.Typer(help="Search prior notes and reports.")

app.add_typer(config_app, name="config")
app.add_typer(onboarding_app, name="onboarding")
app.add_typer(history_app, name="history")


def repo_root() -> Path:
    return Path.cwd()


def require_profile(root: Path) -> Path:
    profile_path = current_profile_markdown_path(root)
    if not profile_path.exists():
        raise typer.Exit("No current profile found. Run `eagle-optimize onboarding run` first.")
    return profile_path


@config_app.command("init")
def config_init() -> None:
    """Create or update local machine config."""
    existing = load_config()
    claude_command = typer.prompt("Claude command", default=existing.claude_command)
    mirror_to_obsidian = typer.confirm(
        "Mirror reports into an Obsidian vault?",
        default=existing.mirror_to_obsidian,
    )
    obsidian_vault_path = existing.obsidian_vault_path
    if mirror_to_obsidian:
        obsidian_vault_path = typer.prompt(
            "Obsidian vault path",
            default=existing.obsidian_vault_path,
            show_default=bool(existing.obsidian_vault_path),
        )
    config = AppConfig(
        backend="claude-code-cli",
        claude_command=claude_command,
        mirror_to_obsidian=mirror_to_obsidian,
        obsidian_vault_path=obsidian_vault_path,
    )
    config_path = save_config(config)
    typer.echo(f"Saved config to {config_path}")


@config_app.command("show")
def config_show() -> None:
    """Show the resolved local config."""
    config = load_config()
    typer.echo(f"backend: {config.backend}")
    typer.echo(f"claude_command: {config.claude_command}")
    typer.echo(f"mirror_to_obsidian: {config.mirror_to_obsidian}")
    typer.echo(f"obsidian_vault_path: {config.obsidian_vault_path or '(not set)'}")


@app.command()
def doctor() -> None:
    """Check Claude CLI availability and auth state."""
    config = load_config()
    backend = ClaudeCliBackend(config.claude_command)
    result = backend.doctor()
    typer.echo(f"command: {result.command}")
    typer.echo(f"available: {result.available}")
    if result.version:
        typer.echo(f"version: {result.version}")
    typer.echo(f"authenticated: {result.authenticated}")
    if result.auth_detail:
        typer.echo(result.auth_detail)


@onboarding_app.command("run")
def onboarding_run(name: Optional[str] = typer.Option(None, help="Descriptive assessment name.")) -> None:
    """Run the reusable onboarding questionnaire."""
    root = repo_root()
    ensure_repo_layout(root)
    existing_answers = load_json(current_profile_json_path(root))
    answers = collect_onboarding_answers(existing_answers)

    timestamp = now_timestamp()
    assessment_base = camel_case_slug(name or answers.get("primary_goals", "currentProfile"), fallback="currentProfile")
    assessment_stem = f"{assessment_base}_assessment_{timestamp}"
    assessment_title = f"{assessment_base}_assessment"

    current_profile_md = render_current_profile_markdown(answers, datetime.now().isoformat(timespec="seconds"))
    assessment_md = render_assessment_markdown(answers, assessment_title, datetime.now().isoformat(timespec="seconds"))

    current_json_path = current_profile_json_path(root)
    current_md_path = current_profile_markdown_path(root)
    assessment_md_path, assessment_json_path = assessment_paths(root, assessment_stem)

    write_json(current_json_path, answers)
    write_text(current_md_path, current_profile_md)
    write_text(assessment_md_path, assessment_md)
    write_json(assessment_json_path, answers)

    config = load_config()
    mirror_path = mirror_markdown_file(config, root, current_md_path)
    mirror_assessment_path = mirror_markdown_file(config, root, assessment_md_path)

    typer.secho("Onboarding saved.", fg=typer.colors.GREEN, bold=True)
    typer.echo(f"Current profile: {repo_relative_path(root, current_md_path)}")
    typer.echo(f"Assessment: {repo_relative_path(root, assessment_md_path)}")
    if mirror_path:
        typer.echo(f"Obsidian profile mirror: {mirror_path}")
    if mirror_assessment_path:
        typer.echo(f"Obsidian assessment mirror: {mirror_assessment_path}")


@app.command()
def ask(
    query: str = typer.Argument(..., help="Optimization question to send to Claude."),
    category: Optional[str] = typer.Option(None, help="Optional category override."),
    title: Optional[str] = typer.Option(None, help="Optional report title override."),
) -> None:
    """Ask a note-aware question and save a categorized report."""
    root = repo_root()
    ensure_repo_layout(root)
    profile_path = require_profile(root)
    profile_markdown = profile_path.read_text(encoding="utf-8")

    config = load_config()
    backend = ClaudeCliBackend(config.claude_command)
    doctor_result = backend.doctor()
    if not doctor_result.available:
        raise typer.Exit("Claude CLI is not available. Install Claude Code first.")
    if not doctor_result.authenticated:
        raise typer.Exit("Claude CLI is not authenticated. Run `claude` and log in first.")

    related_results = search_notes(root, query, limit=5)
    related_context = render_context_bundle(root, related_results)
    requested_folder = guess_category_folder(query, explicit_value=category)

    try:
        result = backend.answer_question(
            repo_root=root,
            query=query,
            requested_category=requested_folder,
            profile_markdown=profile_markdown,
            related_notes=related_context,
        )
    except BackendError as error:
        raise typer.Exit(str(error)) from error

    output_folder = guess_category_folder(query, explicit_value=str(result.get("category", requested_folder)))
    report_stem = camel_case_slug(title or str(result.get("title", query)), fallback="optimizationReport")
    report_filename = f"{report_stem}_{now_timestamp()}_report"
    output_path = optimization_report_path(root, output_folder, report_filename)
    report_markdown = render_optimization_report(
        repo_root=root,
        result=result,
        query=query,
        output_path=output_path,
        related_paths=[item.path for item in related_results],
        created_at=datetime.now().isoformat(timespec="seconds"),
    )
    write_text(output_path, report_markdown)

    mirror_path = mirror_markdown_file(config, root, output_path)

    typer.secho("Short answer", fg=typer.colors.GREEN, bold=True)
    for line in result.get("terminal_summary", []):
        typer.echo(f"- {line}")
    typer.echo("")
    typer.echo(f"Saved report: {repo_relative_path(root, output_path)}")
    if mirror_path:
        typer.echo(f"Obsidian mirror: {mirror_path}")


@history_app.command("search")
def history_search(query: str = typer.Argument(..., help="Search term for prior reports and notes.")) -> None:
    """Search local markdown notes for related history."""
    root = repo_root()
    ensure_repo_layout(root)
    results = search_notes(root, query, limit=10)
    if not results:
        typer.echo("No matching notes found.")
        return

    for index, item in enumerate(results, start=1):
        typer.secho(f"{index}. {repo_relative_path(root, item.path)}", fg=typer.colors.CYAN, bold=True)
        typer.echo(f"   score: {item.score}")
        typer.echo(f"   {item.excerpt[:180]}")


@history_app.command("latest-assessment")
def history_latest_assessment() -> None:
    """Show the newest onboarding assessment file."""
    root = repo_root()
    latest = latest_assessment_markdown(root)
    if not latest:
        typer.echo("No assessment found.")
        return
    typer.echo(repo_relative_path(root, latest))