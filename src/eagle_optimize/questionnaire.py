from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import typer


@dataclass(frozen=True)
class Question:
    key: str
    label: str
    prompt: str
    help_text: str = ""


@dataclass(frozen=True)
class Section:
    title: str
    description: str
    questions: List[Question]


ONBOARDING_SECTIONS = [
    Section(
        title="Core profile",
        description="Baseline identity and context.",
        questions=[
            Question("age", "Age", "Age"),
            Question("sex_gender", "Sex and gender", "Sex and gender"),
            Question(
                "genetic_background",
                "Race or genetic background",
                "Race or genetic background",
                "Include ancestry context relevant to digestion, medication sensitivity, or family history.",
            ),
            Question("height_weight", "Height and weight", "Height and weight"),
            Question("primary_goals", "Primary goals", "Primary goals"),
        ],
    ),
    Section(
        title="Medical context",
        description="Known conditions, limitations, and clinical guidance.",
        questions=[
            Question("medical_limitations", "Medical limitations", "Medical limitations or diagnoses"),
            Question("allergies_intolerances", "Allergies and intolerances", "Allergies or intolerances"),
            Question("current_medications", "Current medications", "Current medications and typical doses"),
            Question("current_supplements", "Current supplements", "Current supplements and timing"),
            Question("clinician_guidance", "Clinician guidance", "Relevant clinician guidance or restrictions"),
            Question("recent_labs", "Recent labs", "Recent labs or health markers"),
        ],
    ),
    Section(
        title="Routine and recovery",
        description="The day-to-day patterns that change recommendations.",
        questions=[
            Question("sleep_pattern", "Sleep pattern", "Sleep pattern and sleep quality"),
            Question("work_pattern", "Work pattern", "Work pattern, schedule, and major time constraints"),
            Question("meal_pattern", "Meal pattern", "Meal timing, appetite pattern, and hydration baseline"),
            Question("stress_mood", "Stress and mood", "Stress, mood baseline, and focus issues"),
        ],
    ),
    Section(
        title="Movement and physical capacity",
        description="What the user can currently tolerate.",
        questions=[
            Question("physical_activity", "Physical activity", "Current physical activities and training load"),
            Question("movement_capacity", "Movement capacity", "Movement capability, stretching tolerance, and injuries"),
            Question("body_feedback", "Body feedback", "Pain, stiffness, digestion, energy, or other body feedback patterns"),
        ],
    ),
    Section(
        title="Substances and experiments",
        description="Substances, sensitivities, and prior results.",
        questions=[
            Question(
                "substance_use",
                "Substance use",
                "Caffeine, nicotine, alcohol, cannabis, or other substance use",
            ),
            Question(
                "digestive_responses",
                "Digestive responses",
                "Known food reactions or digestive responses that went well or badly",
            ),
            Question(
                "experiment_history",
                "Experiment history",
                "Previous experiments, protocols, or routines that helped or failed",
            ),
            Question(
                "missing_context",
                "Missing context",
                "Anything else Claude should know before making recommendations",
            ),
        ],
    ),
]


def collect_onboarding_answers(existing_answers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    answers: Dict[str, str] = {}
    prior = existing_answers or {}

    typer.echo("Run the questionnaire as plain text. Use semicolons for lists.")
    for section in ONBOARDING_SECTIONS:
        typer.secho(f"\n{section.title}", fg=typer.colors.CYAN, bold=True)
        typer.echo(section.description)
        for question in section.questions:
            if question.help_text:
                typer.echo(f"  {question.help_text}")
            default_value = prior.get(question.key, "")
            answers[question.key] = typer.prompt(question.prompt, default=default_value, show_default=bool(default_value)).strip()
    return answers


def section_map() -> Dict[str, Section]:
    return {section.title: section for section in ONBOARDING_SECTIONS}