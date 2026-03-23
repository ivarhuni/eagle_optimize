from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List, Optional

from eagle_optimize.questionnaire import ONBOARDING_SECTIONS
from eagle_optimize.storage import FOLDER_TO_CATEGORY, camel_case_slug, normalize_category_input, repo_relative_path


CATEGORY_KEYWORDS = {
    "foodLiquids": ["food", "milk", "water", "drink", "meal", "protein", "carb", "hydration", "caffeine"],
    "drugsSupplements": ["dose", "dosage", "medication", "medicine", "supplement", "adhd", "nicotine", "alcohol", "cannabis"],
    "mentalHeadspace": ["focus", "mood", "anxiety", "stress", "motivation", "mindset", "meditation"],
    "body": ["pain", "workout", "injury", "digestion", "strength", "fatigue", "mobility"],
    "dailyRoutine": ["routine", "schedule", "sleep", "morning", "evening", "habit", "workflow"],
}


def guess_category_folder(query: str, explicit_value: Optional[str] = None) -> str:
    if explicit_value:
        normalized = normalize_category_input(explicit_value)
        if normalized:
            return normalized

    lowered = query.lower()
    scored = []
    for folder, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for keyword in keywords if keyword in lowered)
        scored.append((score, folder))
    scored.sort(reverse=True)
    top_score, top_folder = scored[0]
    return top_folder if top_score > 0 else "dailyRoutine"


def render_current_profile_markdown(answers: Dict[str, str], updated_at: str) -> str:
    lines = [
        "---",
        "document_type: current_profile",
        f"updated_at: {updated_at}",
        "---",
        "",
        "# Current Profile",
        "",
        "This file is the latest canonical profile used for question answering.",
        "",
    ]
    for section in ONBOARDING_SECTIONS:
        lines.append(f"## {section.title}")
        lines.append("")
        for question in section.questions:
            value = answers.get(question.key, "") or "Not provided"
            lines.append(f"- {question.label}: {value}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_assessment_markdown(answers: Dict[str, str], assessment_name: str, created_at: str) -> str:
    lines = [
        "---",
        "document_type: onboarding_assessment",
        f"assessment_name: {assessment_name}",
        f"created_at: {created_at}",
        "---",
        "",
        f"# {assessment_name}",
        "",
        "Structured onboarding snapshot.",
        "",
    ]
    for section in ONBOARDING_SECTIONS:
        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(section.description)
        lines.append("")
        for question in section.questions:
            value = answers.get(question.key, "") or "Not provided"
            lines.append(f"### {question.label}")
            lines.append("")
            lines.append(value)
            lines.append("")
    return "\n".join(lines).strip() + "\n"


def render_optimization_report(
    repo_root: Path,
    result: Dict[str, object],
    query: str,
    output_path: Path,
    related_paths: Iterable[Path],
    created_at: str,
) -> str:
    category_folder = output_path.parent.name
    category_label = FOLDER_TO_CATEGORY.get(category_folder, result.get("category", "Daily Routine"))
    title = str(result.get("title") or camel_case_slug(query, fallback="optimizationReport"))
    summary_lines = [f"- {line}" for line in result.get("terminal_summary", [])]
    reasoning_lines = [f"- {line}" for line in result.get("reasoning", [])]
    follow_up_lines = [f"- {line}" for line in result.get("follow_up_questions", [])]
    maintenance_lines = [f"- {line}" for line in result.get("profile_updates", [])]
    conflict_lines = [f"- {line}" for line in result.get("conflicts_or_gaps", [])]
    source_lines = [f"- {repo_relative_path(repo_root, path)}" for path in related_paths]

    reference_lines: List[str] = []
    for reference in result.get("references", []):
        label = reference.get("label", "Unnamed reference")
        note = reference.get("note", "")
        source_kind = reference.get("source_kind", "general_guidance")
        reference_lines.append(f"- {label} ({source_kind}): {note}")

    lines = [
        "---",
        "document_type: optimization_report",
        f"created_at: {created_at}",
        f"category: {category_label}",
        f"query: {query}",
        "---",
        "",
        f"# {title}",
        "",
        "## Terminal Summary",
        "",
        *summary_lines,
        "",
        "## Short Answer",
        "",
        str(result.get("short_answer", "")),
        "",
        "## Detailed Answer",
        "",
        str(result.get("detailed_answer", "")),
        "",
        "## Reasoning",
        "",
        *(reasoning_lines or ["- No reasoning was returned."]),
        "",
        "## References",
        "",
        *(reference_lines or ["- No concrete references were available; reasoning was used instead."]),
        "",
        "## Follow-up Questions",
        "",
        *(follow_up_lines or ["- None."]),
        "",
        "## Profile Maintenance",
        "",
        *(maintenance_lines or ["- No profile updates suggested."]),
        "",
        "## Conflicts or Gaps",
        "",
        *(conflict_lines or ["- No conflicts were detected from the provided context."]),
        "",
        "## Source Notes Used",
        "",
        *(source_lines or ["- No prior note matched the query."]),
        "",
    ]
    return "\n".join(lines).strip() + "\n"