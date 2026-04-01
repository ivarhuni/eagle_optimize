from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, dataclass
from pathlib import Path


APP_DIR_NAME = "eagle-optimize"
CONFIG_FILE_NAME = "config.json"
OBSIDIAN_MIRROR_ROOT = "EagleOptimize"


@dataclass
class AppConfig:
    backend: str = "claude-code-cli"
    claude_command: str = "claude"
    copilot_command: str = "copilot"
    obsidian_vault_path: str = ""
    mirror_to_obsidian: bool = True


def get_config_dir() -> Path:
    if os.name == "nt":
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / APP_DIR_NAME
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    return Path.home() / ".config" / APP_DIR_NAME


def get_config_path() -> Path:
    return get_config_dir() / CONFIG_FILE_NAME


def load_config() -> AppConfig:
    config_path = get_config_path()
    if not config_path.exists():
        return AppConfig()

    data = json.loads(config_path.read_text(encoding="utf-8"))
    return AppConfig(
        backend=data.get("backend", "claude-code-cli"),
        claude_command=data.get("claude_command", "claude"),
        copilot_command=data.get("copilot_command", "copilot"),
        obsidian_vault_path=data.get("obsidian_vault_path", ""),
        mirror_to_obsidian=bool(data.get("mirror_to_obsidian", True)),
    )


def save_config(config: AppConfig) -> Path:
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = get_config_path()
    config_path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")
    return config_path


def has_obsidian_mirror(config: AppConfig) -> bool:
    return config.mirror_to_obsidian and bool(config.obsidian_vault_path.strip())