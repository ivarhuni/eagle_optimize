from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


class BackendError(RuntimeError):
    """Raised when the Claude backend cannot complete a request."""


@dataclass
class ClaudeDoctorResult:
    command: str
    available: bool
    version: str
    authenticated: bool
    auth_detail: str


RESPONSE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "category": {
            "type": "string",
            "enum": [
                "Food & Liquids",
                "Drugs and Supplements",
                "Mental Headspace",
                "Body",
                "Daily Routine",
            ],
        },
        "terminal_summary": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 4,
        },
        "short_answer": {"type": "string"},
        "detailed_answer": {"type": "string"},
        "reasoning": {
            "type": "array",
            "items": {"type": "string"},
        },
        "references": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "label": {"type": "string"},
                    "note": {"type": "string"},
                    "source_kind": {
                        "type": "string",
                        "enum": ["provided_note", "general_guidance", "insufficient_source"],
                    },
                },
                "required": ["label", "note", "source_kind"],
            },
        },
        "follow_up_questions": {
            "type": "array",
            "items": {"type": "string"},
        },
        "profile_updates": {
            "type": "array",
            "items": {"type": "string"},
        },
        "conflicts_or_gaps": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": [
        "title",
        "category",
        "terminal_summary",
        "short_answer",
        "detailed_answer",
        "reasoning",
        "references",
        "follow_up_questions",
        "profile_updates",
        "conflicts_or_gaps",
    ],
}


class ClaudeCliBackend:
    def __init__(self, command: str = "claude") -> None:
        self.command = command

    def doctor(self) -> ClaudeDoctorResult:
        available = bool(shutil.which(self.command)) or Path(self.command).exists()
        if not available:
            return ClaudeDoctorResult(
                command=self.command,
                available=False,
                version="",
                authenticated=False,
                auth_detail="Command not found.",
            )

        version_result = subprocess.run(
            [self.command, "-v"],
            capture_output=True,
            text=True,
            check=False,
        )
        auth_result = subprocess.run(
            [self.command, "auth", "status"],
            capture_output=True,
            text=True,
            check=False,
        )
        return ClaudeDoctorResult(
            command=self.command,
            available=True,
            version=version_result.stdout.strip(),
            authenticated=auth_result.returncode == 0,
            auth_detail=(auth_result.stdout or auth_result.stderr).strip(),
        )

    def answer_question(
        self,
        repo_root: Path,
        query: str,
        requested_category: str,
        profile_markdown: str,
        related_notes: str,
    ) -> Dict[str, object]:
        prompt = self._build_prompt(query, requested_category, profile_markdown, related_notes)
        command = [
            self.command,
            "-p",
            "Use the provided context bundle and return only JSON that matches the schema.",
            "--json-schema",
            json.dumps(RESPONSE_SCHEMA),
            "--max-turns",
            "5",
            "--no-session-persistence",
        ]
        result = subprocess.run(
            command,
            input=prompt,
            capture_output=True,
            text=True,
            cwd=str(repo_root),
            check=False,
        )
        if result.returncode != 0:
            raise BackendError((result.stderr or result.stdout).strip() or "Claude CLI failed.")

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as error:
            raise BackendError(f"Claude returned invalid JSON: {error}") from error

    @staticmethod
    def _build_prompt(query: str, requested_category: str, profile_markdown: str, related_notes: str) -> str:
        return f"""
You are generating a personalized optimization note for a CLI tool.

Requirements:
- Personalize your answer using only the provided profile and note context.
- Be explicit when context is missing or ambiguous.
- Do not fabricate citations, URLs, paper titles, or lab values.
- If a statement is grounded in a provided note, mark it as a provided_note reference.
- If you rely on broadly accepted guidance without a concrete source in context, mark it as general_guidance.
- If evidence is too thin, mark it as insufficient_source.
- For prescription medications, controlled substances, diagnoses, or dosing questions: do not prescribe, do not tell the user to start, stop, or change a medication plan. Instead summarize relevant user context, identify safety flags, and frame the answer as information to discuss with a licensed clinician.
- The short answer should stay concise enough for terminal display.
- The detailed answer should be a useful Markdown-ready body.
- The profile_updates field should list changes the user may want to add back into onboarding data after this session.
- The conflicts_or_gaps field should highlight missing data or contradictions in the supplied notes.

Requested category: {requested_category}

User question:
{query}

Current profile:
{profile_markdown}

Relevant prior notes:
{related_notes}
""".strip()