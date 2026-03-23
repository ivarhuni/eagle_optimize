import re

from typer.testing import CliRunner

from eagle_optimize.banner import render_startup_banner
from eagle_optimize.cli import app


runner = CliRunner()


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_render_startup_banner_plaintext_has_portrait_shape() -> None:
    banner = render_startup_banner(color=False)
    assert ".-~~~~~~~~~~-." in banner
    assert "| () |" in banner
    assert "_/ || \\_" in banner


def test_render_startup_banner_color_mode_adds_ansi() -> None:
    banner = render_startup_banner()
    assert "\x1b[38;5;" in banner


def test_cli_without_tty_shows_help_without_banner() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    plain_output = strip_ansi(result.stdout)
    assert "Usage:" in plain_output
    assert ".-~~~~~~~~~~-." not in plain_output


def test_cli_prints_banner_before_command_output_when_enabled(monkeypatch) -> None:
    monkeypatch.setattr("eagle_optimize.cli.should_render_startup_banner", lambda: True)
    monkeypatch.setattr("eagle_optimize.cli.render_startup_banner", lambda: "PORTRAIT")
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert result.stdout.startswith("PORTRAIT\n\n")
    assert "backend:" in result.stdout