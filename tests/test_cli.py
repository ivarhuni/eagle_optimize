import re
from pathlib import Path
from typing import Dict, List

from typer.testing import CliRunner

from eagle_optimize import banner as banner_module
from eagle_optimize.banner import render_startup_banner
from eagle_optimize.cli import app, resolve_backend_name
from eagle_optimize.config import AppConfig


runner = CliRunner()


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_render_startup_banner_plaintext_is_non_empty_and_multiline() -> None:
    banner = render_startup_banner(color=False)
    non_empty_lines = [line for line in banner.splitlines() if line.strip()]
    assert banner.strip()
    assert len(non_empty_lines) > 1


def test_banner_library_contains_exactly_100_ascii_arts() -> None:
    assert len(banner_module._ASCII_ART_LIBRARY) == 100


def test_render_startup_banner_can_be_deterministic_with_monkeypatched_random_choice(monkeypatch) -> None:
    expected = "first line\nsecond line"
    monkeypatch.setattr("eagle_optimize.banner.random.choice", lambda _arts: expected)
    banner = render_startup_banner(color=False)
    assert banner == expected


def test_render_startup_banner_color_mode_adds_ansi() -> None:
    banner = render_startup_banner()
    assert "\x1b[38;5;" in banner


def test_cli_without_tty_shows_help_without_banner() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    plain_output = strip_ansi(result.stdout)
    assert plain_output.lstrip().startswith("Usage:")
    assert "Personal optimization CLI backed by Claude Code or GitHub Copilot CLI." in plain_output
    assert "ask" in plain_output


def test_cli_prints_banner_before_command_output_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr("eagle_optimize.cli.should_render_startup_banner", lambda: True)
    monkeypatch.setattr("eagle_optimize.cli.render_startup_banner", lambda: "PORTRAIT")
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert result.stdout.startswith("PORTRAIT\n\n")
    assert "backend:" in result.stdout


def test_backend_resolution_precedence_and_default() -> None:
    assert resolve_backend_name("github-copilot-cli", "claude-code-cli") == "github-copilot-cli"
    assert resolve_backend_name(None, "github-copilot-cli") == "github-copilot-cli"
    assert resolve_backend_name("copilot", "claude-code-cli") == "github-copilot-cli"
    assert resolve_backend_name(None, "") == "claude-code-cli"


def test_doctor_dispatches_to_selected_backend(monkeypatch) -> None:
    calls: List[str] = []

    class FakeClaudeBackend:
        def __init__(self, command: str) -> None:
            calls.append(f"claude_init:{command}")

        def doctor(self) -> Dict[str, object]:
            calls.append("claude_doctor")
            return {
                "command": "claude-cmd",
                "available": True,
                "version": "1.0",
                "authenticated": True,
                "auth_detail": "ok",
            }

    class FakeCopilotBackend:
        def __init__(self, command: str) -> None:
            calls.append(f"copilot_init:{command}")

        def doctor(self) -> Dict[str, object]:
            calls.append("copilot_doctor")
            return {
                "command": "copilot-cmd",
                "available": True,
                "version": "2.0",
                "authenticated": True,
                "auth_detail": "ok",
            }

    monkeypatch.setattr(
        "eagle_optimize.cli.load_config",
        lambda: AppConfig(claude_command="claude-cmd", copilot_command="copilot-cmd"),
    )
    monkeypatch.setattr("eagle_optimize.cli.ClaudeCliBackend", FakeClaudeBackend)
    monkeypatch.setattr("eagle_optimize.cli.CopilotCliBackend", FakeCopilotBackend)

    result = runner.invoke(app, ["doctor", "--backend", "github-copilot-cli"])

    assert result.exit_code == 0
    assert "backend: github-copilot-cli" in result.stdout
    assert "command: copilot-cmd" in result.stdout
    assert calls == ["copilot_init:copilot-cmd", "copilot_doctor"]


def test_ask_dispatches_to_selected_backend(monkeypatch) -> None:
    calls: List[str] = []

    class FakeClaudeBackend:
        def __init__(self, command: str) -> None:
            calls.append(f"claude_init:{command}")

        def doctor(self) -> Dict[str, object]:
            calls.append("claude_doctor")
            return {
                "command": "claude-cmd",
                "available": True,
                "version": "1.0",
                "authenticated": True,
                "auth_detail": "ok",
            }

        def answer_question(self, **_: object) -> Dict[str, object]:
            calls.append("claude_answer")
            return {}

    class FakeCopilotBackend:
        def __init__(self, command: str) -> None:
            calls.append(f"copilot_init:{command}")

        def doctor(self) -> Dict[str, object]:
            calls.append("copilot_doctor")
            return {
                "command": "copilot-cmd",
                "available": True,
                "version": "2.0",
                "authenticated": True,
                "auth_detail": "ok",
            }

        def answer_question(self, **_: object) -> Dict[str, object]:
            calls.append("copilot_answer")
            return {
                "title": "Quick check",
                "category": "Daily Routine",
                "terminal_summary": ["summary line"],
                "short_answer": "short",
                "detailed_answer": "detailed",
                "reasoning": ["reason"],
                "references": [],
                "follow_up_questions": [],
                "profile_updates": [],
                "conflicts_or_gaps": [],
            }

    monkeypatch.setattr(
        "eagle_optimize.cli.load_config",
        lambda: AppConfig(claude_command="claude-cmd", copilot_command="copilot-cmd"),
    )
    monkeypatch.setattr("eagle_optimize.cli.ClaudeCliBackend", FakeClaudeBackend)
    monkeypatch.setattr("eagle_optimize.cli.CopilotCliBackend", FakeCopilotBackend)
    monkeypatch.setattr("eagle_optimize.cli.search_notes", lambda *_args, **_kwargs: [])
    monkeypatch.setattr("eagle_optimize.cli.render_context_bundle", lambda *_args, **_kwargs: "")
    monkeypatch.setattr("eagle_optimize.cli.mirror_markdown_file", lambda *_args, **_kwargs: None)

    with runner.isolated_filesystem():
        profile_path = Path("profiles/current_profile.md")
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("# Current Profile\n", encoding="utf-8")

        result = runner.invoke(app, ["ask", "How can I improve focus?", "--backend", "github-copilot-cli"])

    assert result.exit_code == 0
    assert "Saved report:" in result.stdout
    assert "copilot_answer" in calls
    assert "claude_answer" not in calls


def _full_response(**overrides) -> Dict[str, object]:
    base: Dict[str, object] = {
        "title": "Milk Check",
        "category": "Food & Liquids",
        "terminal_summary": ["Milk is generally fine in moderation."],
        "short_answer": "Milk is fine for most people.",
        "detailed_answer": "Detailed answer about milk.",
        "reasoning": ["Reason 1"],
        "references": [],
        "follow_up_questions": [],
        "profile_updates": [],
        "conflicts_or_gaps": [],
    }
    base.update(overrides)
    return base


def _make_fake_backends(monkeypatch, doctor_result=None, answer_result=None, answer_error=None):
    """Patch both backend classes with controllable fakes."""
    if doctor_result is None:
        doctor_result = {
            "command": "claude-cmd",
            "available": True,
            "version": "1.0",
            "authenticated": True,
            "auth_detail": "ok",
        }

    class FakeBackend:
        def __init__(self, command: str) -> None:
            pass

        def doctor(self) -> Dict[str, object]:
            return doctor_result

        def answer_question(self, **_: object) -> Dict[str, object]:
            if answer_error:
                raise answer_error
            return answer_result or _full_response()

    monkeypatch.setattr("eagle_optimize.cli.load_config", lambda: AppConfig())
    monkeypatch.setattr("eagle_optimize.cli.ClaudeCliBackend", FakeBackend)
    monkeypatch.setattr("eagle_optimize.cli.CopilotCliBackend", FakeBackend)
    monkeypatch.setattr("eagle_optimize.cli.search_notes", lambda *_a, **_k: [])
    monkeypatch.setattr("eagle_optimize.cli.render_context_bundle", lambda *_a, **_k: "")
    monkeypatch.setattr("eagle_optimize.cli.mirror_markdown_file", lambda *_a, **_k: None)


def test_ask_writes_report_file(monkeypatch) -> None:
    _make_fake_backends(monkeypatch)

    with runner.isolated_filesystem():
        profile_path = Path("profiles/current_profile.md")
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("# Current Profile\n", encoding="utf-8")

        result = runner.invoke(app, ["ask", "Is milk good for me?"])

    assert result.exit_code == 0
    assert "Saved report:" in result.stdout
    assert "Milk is generally fine" in result.stdout


def test_ask_fails_when_no_profile(monkeypatch) -> None:
    _make_fake_backends(monkeypatch)

    with runner.isolated_filesystem():
        Path("profiles").mkdir()
        result = runner.invoke(app, ["ask", "Is milk good?"])

    assert result.exit_code != 0


def test_ask_fails_when_backend_not_available(monkeypatch) -> None:
    _make_fake_backends(
        monkeypatch,
        doctor_result={
            "command": "claude",
            "available": False,
            "version": "",
            "authenticated": False,
            "auth_detail": "Command not found.",
        },
    )

    with runner.isolated_filesystem():
        profile_path = Path("profiles/current_profile.md")
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("# Current Profile\n", encoding="utf-8")

        result = runner.invoke(app, ["ask", "Test question"])

    assert result.exit_code != 0


def test_ask_fails_when_backend_not_authenticated(monkeypatch) -> None:
    _make_fake_backends(
        monkeypatch,
        doctor_result={
            "command": "claude",
            "available": True,
            "version": "1.0",
            "authenticated": False,
            "auth_detail": "Not authenticated.",
        },
    )

    with runner.isolated_filesystem():
        profile_path = Path("profiles/current_profile.md")
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("# Current Profile\n", encoding="utf-8")

        result = runner.invoke(app, ["ask", "Test question"])

    assert result.exit_code != 0


def test_ask_backend_error_propagates(monkeypatch) -> None:
    from eagle_optimize.claude_bridge import BackendError

    _make_fake_backends(
        monkeypatch,
        answer_error=BackendError("Something broke in the backend"),
    )

    with runner.isolated_filesystem():
        profile_path = Path("profiles/current_profile.md")
        profile_path.parent.mkdir(parents=True, exist_ok=True)
        profile_path.write_text("# Current Profile\n", encoding="utf-8")

        result = runner.invoke(app, ["ask", "Test question"])

    assert result.exit_code != 0


def test_config_init_allows_selecting_copilot_backend(monkeypatch) -> None:
    captured: Dict[str, AppConfig] = {}

    monkeypatch.setattr(
        "eagle_optimize.cli.load_config",
        lambda: AppConfig(
            backend="claude-code-cli",
            claude_command="claude",
            copilot_command="copilot",
            mirror_to_obsidian=False,
            obsidian_vault_path="",
        ),
    )

    def fake_save_config(config: AppConfig) -> Path:
        captured["saved"] = config
        return Path("/tmp/config.json")

    monkeypatch.setattr("eagle_optimize.cli.save_config", fake_save_config)

    result = runner.invoke(app, ["config", "init"], input="copilot\n\n\nN\n")

    assert result.exit_code == 0
    assert captured["saved"].backend == "github-copilot-cli"