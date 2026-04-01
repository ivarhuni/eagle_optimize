import json

from eagle_optimize.config import AppConfig, load_config, save_config


def test_load_config_uses_default_copilot_command_when_missing(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "backend": "claude-code-cli",
                "claude_command": "claude",
                "obsidian_vault_path": "",
                "mirror_to_obsidian": True,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr("eagle_optimize.config.get_config_path", lambda: config_path)

    loaded = load_config()

    assert loaded.backend == "claude-code-cli"
    assert loaded.claude_command == "claude"
    assert loaded.copilot_command == "copilot"


def test_save_and_load_config_persists_copilot_command(tmp_path, monkeypatch) -> None:
    config_dir = tmp_path / "cfg"
    config_path = config_dir / "config.json"

    monkeypatch.setattr("eagle_optimize.config.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("eagle_optimize.config.get_config_path", lambda: config_path)

    save_config(
        AppConfig(
            backend="github-copilot-cli",
            claude_command="claude",
            copilot_command="copilot --mode chat",
            obsidian_vault_path="",
            mirror_to_obsidian=False,
        )
    )

    persisted = json.loads(config_path.read_text(encoding="utf-8"))
    loaded = load_config()

    assert persisted["copilot_command"] == "copilot --mode chat"
    assert loaded.backend == "github-copilot-cli"
    assert loaded.copilot_command == "copilot --mode chat"
    assert loaded.mirror_to_obsidian is False
