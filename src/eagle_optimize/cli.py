from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from click import Choice
import typer

from eagle_optimize.banner import render_startup_banner, should_render_startup_banner
from eagle_optimize.claude_bridge import BackendError, ClaudeCliBackend
from eagle_optimize.copilot_bridge import CopilotCliBackend
from eagle_optimize.config import AppConfig, load_config, save_config
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
from eagle_optimize.terminal_loader import run_with_funky_loader


app = typer.Typer(help="Personal optimization CLI backed by Claude Code or GitHub Copilot CLI.")
config_app = typer.Typer(help="Local machine configuration.")
onboarding_app = typer.Typer(help="Onboarding and profile management.")
history_app = typer.Typer(help="Search prior notes and reports.")

app.add_typer(config_app, name="config")
app.add_typer(onboarding_app, name="onboarding")
app.add_typer(history_app, name="history")


DEFAULT_BACKEND = "claude-code-cli"
BACKEND_ALIASES = {
    "claude": "claude-code-cli",
    "claude-code-cli": "claude-code-cli",
    "copilot": "github-copilot-cli",
    "github-copilot-cli": "github-copilot-cli",
}


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    if should_render_startup_banner():
        typer.echo(render_startup_banner())
        typer.echo()

    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def repo_root() -> Path:
    return Path.cwd()


def require_profile(root: Path) -> Path:
    profile_path = current_profile_markdown_path(root)
    if not profile_path.exists():
        raise typer.Exit("No current profile found. Run `eagle-optimize onboarding run` first.")
    return profile_path


def resolve_backend_name(cli_backend: Optional[str], configured_backend: str) -> str:
    selected = (cli_backend or configured_backend or DEFAULT_BACKEND).strip().lower()
    if not selected:
        selected = DEFAULT_BACKEND
    return BACKEND_ALIASES.get(selected, selected)


def build_backend(cli_backend: Optional[str], config: AppConfig) -> Tuple[str, object]:
    backend_name = resolve_backend_name(cli_backend, config.backend)
    if backend_name == "claude-code-cli":
        return backend_name, ClaudeCliBackend(config.claude_command)
    if backend_name == "github-copilot-cli":
        return backend_name, CopilotCliBackend(config.copilot_command)
    raise typer.Exit(
        f"Unsupported backend '{backend_name}'. Supported values: claude-code-cli or github-copilot-cli."
    )


def normalize_doctor_result(result: object) -> Dict[str, object]:
    if isinstance(result, dict):
        return result
    return {
        "command": getattr(result, "command", ""),
        "available": bool(getattr(result, "available", False)),
        "version": getattr(result, "version", ""),
        "authenticated": bool(getattr(result, "authenticated", False)),
        "auth_detail": getattr(result, "auth_detail", ""),
    }


def backend_prompt_default(configured_backend: str) -> str:
    normalized_backend = resolve_backend_name(None, configured_backend)
    if normalized_backend == "github-copilot-cli":
        return "copilot"
    return "claude"


@config_app.command("init")
def config_init() -> None:
    """Create or update local machine config."""
    existing = load_config()
    backend_choice = typer.prompt(
        "Default backend",
        default=backend_prompt_default(existing.backend),
        type=Choice(["claude", "copilot"], case_sensitive=False),
        show_choices=True,
    )
    claude_command = typer.prompt("Claude command", default=existing.claude_command)
    copilot_command = typer.prompt("Copilot command", default=existing.copilot_command)
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
        backend=resolve_backend_name(str(backend_choice), DEFAULT_BACKEND),
        claude_command=claude_command,
        copilot_command=copilot_command,
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
    typer.echo(f"copilot_command: {config.copilot_command}")
    typer.echo(f"mirror_to_obsidian: {config.mirror_to_obsidian}")
    typer.echo(f"obsidian_vault_path: {config.obsidian_vault_path or '(not set)'}")


@app.command()
def doctor(
    backend: Optional[str] = typer.Option(
        None,
        help="Optional backend override: claude-code-cli or github-copilot-cli.",
    )
) -> None:
    """Check backend CLI availability and auth state."""
    config = load_config()
    selected_backend, backend_client = build_backend(backend, config)
    result = normalize_doctor_result(backend_client.doctor())
    typer.echo(f"backend: {selected_backend}")
    typer.echo(f"command: {result.get('command', '')}")
    typer.echo(f"available: {result.get('available', False)}")
    if result.get("version"):
        typer.echo(f"version: {result.get('version')}")
    typer.echo(f"authenticated: {result.get('authenticated', False)}")
    if result.get("auth_detail"):
        typer.echo(str(result.get("auth_detail")))


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
    query: str = typer.Argument(..., help="Optimization question to send to the selected backend."),
    category: Optional[str] = typer.Option(None, help="Optional category override."),
    title: Optional[str] = typer.Option(None, help="Optional report title override."),
    backend: Optional[str] = typer.Option(
        None,
        help="Optional backend override: claude-code-cli or github-copilot-cli.",
    ),
) -> None:
    """Ask a note-aware question and save a categorized report."""
    root = repo_root()
    ensure_repo_layout(root)
    profile_path = require_profile(root)
    profile_markdown = profile_path.read_text(encoding="utf-8")

    config = load_config()
    selected_backend, backend_client = build_backend(backend, config)
    doctor_result = normalize_doctor_result(backend_client.doctor())
    if not doctor_result.get("available", False):
        raise typer.Exit(
            f"{selected_backend} command is not available. Configure the backend command via `eagle-optimize config init`."
        )
    if not doctor_result.get("authenticated", False):
        auth_detail = str(doctor_result.get("auth_detail", "")).strip()
        detail = f" Details: {auth_detail}" if auth_detail else ""
        raise typer.Exit(f"{selected_backend} is not authenticated.{detail}")

    related_results = search_notes(root, query, limit=5)
    related_context = render_context_bundle(root, related_results)
    requested_folder = guess_category_folder(query, explicit_value=category)

    try:
        with run_with_funky_loader(message="Synthesizing your optimization answer"):
            result = backend_client.answer_question(
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