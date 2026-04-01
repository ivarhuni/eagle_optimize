from __future__ import annotations

import json
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from eagle_optimize.claude_bridge import BackendError, RESPONSE_SCHEMA


class CopilotCliBackend:
    def __init__(self, command: str = "copilot") -> None:
        self.command = command

    def _command_tokens(self) -> List[str]:
        tokens = shlex.split(self.command)
        if not tokens:
            raise BackendError("Copilot command is empty. Set a valid copilot_command in config.")
        return tokens

    def doctor(self) -> Dict[str, object]:
        tokens = self._command_tokens()
        executable = tokens[0]
        available = bool(shutil.which(executable)) or Path(executable).exists()
        if not available:
            return {
                "command": self.command,
                "available": False,
                "version": "",
                "authenticated": False,
                "auth_detail": "Command not found.",
            }

        version = ""
        version_result = subprocess.run(
            [*tokens, "--version"],
            capture_output=True,
            text=True,
            check=False,
        )
        if version_result.returncode == 0:
            version = (version_result.stdout or version_result.stderr).strip()

        authenticated, auth_detail = self._doctor_auth_status(tokens)

        return {
            "command": self.command,
            "available": True,
            "version": version,
            "authenticated": authenticated,
            "auth_detail": auth_detail,
        }

    @staticmethod
    def _is_prompt_mode_auth_hint(text: str) -> bool:
        lowered = text.lower()
        return (
            "invalid command format" in lowered
            or "did you mean: copilot -i" in lowered
            or "for non-interactive mode, use the -p" in lowered
            or ("unknown" in lowered and "command" in lowered)
        )

    def _doctor_auth_status(self, tokens: List[str]) -> Tuple[bool, str]:
        auth_result = subprocess.run(
            [*tokens, "auth", "status"],
            capture_output=True,
            text=True,
            check=False,
        )
        auth_output = (auth_result.stdout or auth_result.stderr).strip()
        if auth_result.returncode == 0:
            return True, auth_output or "Authentication is configured."

        if self._is_prompt_mode_auth_hint(auth_output):
            return self._prompt_mode_auth_probe(tokens)

        return False, auth_output or "Authentication check failed."

    @staticmethod
    def _prompt_mode_auth_probe(tokens: List[str]) -> Tuple[bool, str]:
        # Newer Copilot CLI builds are prompt-first and do not support `auth status`.
        # A successful non-interactive prompt call implies the local auth token is usable.
        try:
            probe_result = subprocess.run(
                [
                    *tokens,
                    "-p",
                    "Reply with exactly OK.",
                    "-s",
                    "--allow-all",
                    "--no-alt-screen",
                    "--no-color",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            return False, "Prompt-mode auth probe timed out."

        probe_output = (probe_result.stdout or probe_result.stderr).strip()
        if probe_result.returncode == 0:
            return True, probe_output or "Prompt-mode auth probe succeeded."

        lowered = probe_output.lower()
        if "login" in lowered or "authenticate" in lowered or "not logged" in lowered:
            return False, probe_output or "Copilot login is required."

        return False, probe_output or "Prompt-mode auth probe failed."

    def answer_question(
        self,
        repo_root: Path,
        query: str,
        requested_category: str,
        profile_markdown: str,
        related_notes: str,
    ) -> Dict[str, object]:
        prompt = self._build_prompt(query, requested_category, profile_markdown, related_notes)
        tokens = self._command_tokens()

        # Try a couple of common CLI shapes while keeping command selection fully configurable.
        attempts = [
            [
                *tokens,
                "-p",
                prompt,
                "-s",
                "--output-format",
                "json",
                "--allow-all-tools",
                "--no-alt-screen",
                "--no-color",
            ],
            [
                *tokens,
                "-p",
                prompt,
                "-s",
                "--allow-all-tools",
                "--no-alt-screen",
                "--no-color",
            ],
            [*tokens, "chat", "--json"],
            [*tokens, "--json"],
            [*tokens],
        ]

        failures: List[str] = []
        for command in attempts:
            uses_stdin = "-p" not in command and "--prompt" not in command
            result = subprocess.run(
                command,
                input=prompt if uses_stdin else None,
                capture_output=True,
                text=True,
                cwd=str(repo_root),
                check=False,
            )
            if result.returncode != 0:
                stderr = (result.stderr or result.stdout).strip()
                failures.append(f"{' '.join(command)} -> {stderr or 'non-zero exit'}")
                continue

            parsed = self._parse_response_payload(result.stdout)
            if parsed is not None:
                return parsed

            stderr = (result.stderr or "").strip()
            snippet = (result.stdout or "").strip().replace("\n", " ")[:220]
            detail = f" stdout: {snippet}" if snippet else ""
            if stderr:
                detail += f" stderr: {stderr[:180]}"
            failures.append(f"{' '.join(command)} -> could not parse JSON object.{detail}")

        details = "\n".join(failures) if failures else "No command attempts were made."
        raise BackendError(
            "Copilot CLI failed. Configure config.copilot_command to a command that accepts prompt text on stdin "
            "or prompt mode and returns JSON matching the report schema.\n"
            f"Attempted:\n{details}"
        )

    @staticmethod
    def _parse_response_payload(stdout: str) -> Optional[Dict[str, object]]:
        stripped = stdout.strip()
        if not stripped:
            return None

        direct = CopilotCliBackend._json_dict_from_text(stripped)
        if direct is not None:
            return direct

        from_jsonl = CopilotCliBackend._json_dict_from_jsonl(stripped)
        if from_jsonl is not None:
            return from_jsonl

        return CopilotCliBackend._extract_first_json_object(stripped)

    @staticmethod
    def _json_dict_from_text(text: str) -> Optional[Dict[str, object]]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(payload, dict):
            return payload
        return None

    @staticmethod
    def _json_dict_from_jsonl(text: str) -> Optional[Dict[str, object]]:
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue

            if not isinstance(item, dict):
                continue

            if CopilotCliBackend._looks_like_response_object(item):
                return item

            if item.get("type") != "assistant.message":
                continue

            data = item.get("data")
            if not isinstance(data, dict):
                continue

            content = data.get("content")
            if not isinstance(content, str):
                continue

            content_dict = CopilotCliBackend._json_dict_from_text(content.strip())
            if content_dict is not None:
                return content_dict

            extracted = CopilotCliBackend._extract_first_json_object(content)
            if extracted is not None:
                return extracted

        return None

    @staticmethod
    def _extract_first_json_object(text: str) -> Optional[Dict[str, object]]:
        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if fenced_match:
            fenced_payload = CopilotCliBackend._json_dict_from_text(fenced_match.group(1).strip())
            if fenced_payload is not None:
                return fenced_payload

        decoder = json.JSONDecoder()
        for index, character in enumerate(text):
            if character != "{":
                continue
            try:
                candidate, _ = decoder.raw_decode(text[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, dict):
                return candidate
        return None

    @staticmethod
    def _looks_like_response_object(payload: Dict[str, object]) -> bool:
        expected_keys = {
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
        }
        return expected_keys.issubset(set(payload.keys()))

    @staticmethod
    def _build_prompt(query: str, requested_category: str, profile_markdown: str, related_notes: str) -> str:
        return f"""
You are generating a personalized optimization note for a CLI tool.
Return only valid JSON matching this schema:
{json.dumps(RESPONSE_SCHEMA)}

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
