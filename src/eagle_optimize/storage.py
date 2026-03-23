from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from eagle_optimize.config import AppConfig, OBSIDIAN_MIRROR_ROOT, has_obsidian_mirror


CATEGORY_FOLDERS = {
    "Food & Liquids": "foodLiquids",
    "Drugs and Supplements": "drugsSupplements",
    "Mental Headspace": "mentalHeadspace",
    "Body": "body",
    "Daily Routine": "dailyRoutine",
}

FOLDER_TO_CATEGORY = {value: key for key, value in CATEGORY_FOLDERS.items()}


def ensure_repo_layout(repo_root: Path) -> None:
    (repo_root / "profiles").mkdir(exist_ok=True)
    (repo_root / "profiles" / "assessments").mkdir(parents=True, exist_ok=True)
    for folder in CATEGORY_FOLDERS.values():
        (repo_root / "optimizations" / folder).mkdir(parents=True, exist_ok=True)


def now_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def camel_case_slug(text: str, fallback: str = "report") -> str:
    parts = re.findall(r"[A-Za-z0-9]+", text)
    if not parts:
        return fallback
    head = parts[0].lower()
    tail = "".join(part.capitalize() for part in parts[1:7])
    return f"{head}{tail}"


def repo_relative_path(repo_root: Path, path: Path) -> str:
    return path.relative_to(repo_root).as_posix()


def write_json(path: Path, payload: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_json(path: Path) -> Dict[str, str]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def current_profile_json_path(repo_root: Path) -> Path:
    return repo_root / "profiles" / "current_profile.json"


def current_profile_markdown_path(repo_root: Path) -> Path:
    return repo_root / "profiles" / "current_profile.md"


def assessment_paths(repo_root: Path, stem: str) -> Tuple[Path, Path]:
    base = repo_root / "profiles" / "assessments" / stem
    return base.with_suffix(".md"), base.with_suffix(".json")


def optimization_report_path(repo_root: Path, category_folder: str, stem: str) -> Path:
    return repo_root / "optimizations" / category_folder / f"{stem}.md"


def mirror_markdown_file(config: AppConfig, repo_root: Path, source_path: Path) -> Optional[Path]:
    if not has_obsidian_mirror(config):
        return None

    vault_root = Path(config.obsidian_vault_path).expanduser()
    relative_path = source_path.relative_to(repo_root)
    destination = vault_root / OBSIDIAN_MIRROR_ROOT / repo_root.name / relative_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(source_path.read_text(encoding="utf-8"), encoding="utf-8")
    return destination


def normalize_category_input(value: str) -> Optional[str]:
    compact = re.sub(r"[^a-z]", "", value.lower())
    for label, folder in CATEGORY_FOLDERS.items():
        if compact in {
            re.sub(r"[^a-z]", "", label.lower()),
            re.sub(r"[^a-z]", "", folder.lower()),
        }:
            return folder
    return None


def note_files(repo_root: Path) -> List[Path]:
    paths: List[Path] = []
    for root_name in ("profiles", "optimizations"):
        root = repo_root / root_name
        if not root.exists():
            continue
        for path in root.rglob("*.md"):
            if path.name == ".gitkeep":
                continue
            paths.append(path)
    return sorted(paths)


def read_excerpt(path: Path, max_chars: int = 1400) -> str:
    text = path.read_text(encoding="utf-8")
    compact = re.sub(r"\s+", " ", text).strip()
    return compact[:max_chars]


def latest_assessment_markdown(repo_root: Path) -> Optional[Path]:
    assessments_dir = repo_root / "profiles" / "assessments"
    if not assessments_dir.exists():
        return None
    candidates = sorted(assessments_dir.glob("*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    return candidates[0] if candidates else None