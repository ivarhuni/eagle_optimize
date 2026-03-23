from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List

from eagle_optimize.storage import note_files, read_excerpt, repo_relative_path


@dataclass
class RetrievalResult:
    path: Path
    score: int
    excerpt: str


def tokenize(text: str) -> List[str]:
    return [token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2]


def score_note(path: Path, text: str, terms: List[str]) -> int:
    lowered = text.lower()
    filename = path.name.lower()
    score = 0
    for term in terms:
        score += lowered.count(term)
        if term in filename:
            score += 4
    return score


def search_notes(repo_root: Path, query: str, limit: int = 5) -> List[RetrievalResult]:
    terms = tokenize(query)
    results: List[RetrievalResult] = []
    for path in note_files(repo_root):
        text = path.read_text(encoding="utf-8")
        score = score_note(path, text, terms)
        if score <= 0:
            continue
        results.append(RetrievalResult(path=path, score=score, excerpt=read_excerpt(path)))
    results.sort(key=lambda item: (item.score, item.path.stat().st_mtime), reverse=True)
    return results[:limit]


def render_context_bundle(repo_root: Path, results: List[RetrievalResult]) -> str:
    if not results:
        return "No directly relevant prior notes were found."

    blocks = []
    for item in results:
        relative_path = repo_relative_path(repo_root, item.path)
        blocks.append(
            "\n".join(
                [
                    f"Path: {relative_path}",
                    f"Score: {item.score}",
                    f"Excerpt: {item.excerpt}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)