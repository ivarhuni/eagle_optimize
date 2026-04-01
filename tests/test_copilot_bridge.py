import json
import subprocess
from pathlib import Path

import pytest

from eagle_optimize.claude_bridge import BackendError
from eagle_optimize.copilot_bridge import CopilotCliBackend


def test_copilot_doctor_prompt_mode_auth_probe_success(monkeypatch) -> None:
    backend = CopilotCliBackend("copilot")

    def fake_run(args, **_kwargs):
        if args == ["copilot", "--version"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="GitHub Copilot CLI 0.0.420", stderr="")
        if args == ["copilot", "auth", "status"]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="Invalid command format. Did you mean: copilot -i \"auth status\"?",
            )
        if args == [
            "copilot",
            "-p",
            "Reply with exactly OK.",
            "-s",
            "--allow-all",
            "--no-alt-screen",
            "--no-color",
        ]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="OK", stderr="")
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr("eagle_optimize.copilot_bridge.shutil.which", lambda _exe: "/usr/local/bin/copilot")
    monkeypatch.setattr("eagle_optimize.copilot_bridge.subprocess.run", fake_run)

    result = backend.doctor()

    assert result["available"] is True
    assert result["authenticated"] is True
    assert result["auth_detail"] == "OK"


def test_copilot_doctor_prompt_mode_auth_probe_failure(monkeypatch) -> None:
    backend = CopilotCliBackend("copilot")

    def fake_run(args, **_kwargs):
        if args == ["copilot", "--version"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="GitHub Copilot CLI 0.0.420", stderr="")
        if args == ["copilot", "auth", "status"]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="Invalid command format. Did you mean: copilot -i \"auth status\"?",
            )
        if args == [
            "copilot",
            "-p",
            "Reply with exactly OK.",
            "-s",
            "--allow-all",
            "--no-alt-screen",
            "--no-color",
        ]:
            return subprocess.CompletedProcess(
                args=args,
                returncode=1,
                stdout="",
                stderr="Authentication required. Please login.",
            )
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr("eagle_optimize.copilot_bridge.shutil.which", lambda _exe: "/usr/local/bin/copilot")
    monkeypatch.setattr("eagle_optimize.copilot_bridge.subprocess.run", fake_run)

    result = backend.doctor()

    assert result["available"] is True
    assert result["authenticated"] is False
    assert "Authentication required" in str(result["auth_detail"])


def test_copilot_answer_question_raises_on_invalid_json(monkeypatch) -> None:
    backend = CopilotCliBackend("copilot")

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["copilot"], returncode=0, stdout="not-json", stderr="")

    monkeypatch.setattr("eagle_optimize.copilot_bridge.subprocess.run", fake_run)

    with pytest.raises(BackendError, match="Copilot CLI failed"):
        backend.answer_question(
            repo_root=Path("."),
            query="test question",
            requested_category="dailyRoutine",
            profile_markdown="profile",
            related_notes="notes",
        )


def test_copilot_answer_question_raises_on_non_object_json(monkeypatch) -> None:
    backend = CopilotCliBackend("copilot")

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["copilot"], returncode=0, stdout='["not", "an", "object"]', stderr="")

    monkeypatch.setattr("eagle_optimize.copilot_bridge.subprocess.run", fake_run)

    with pytest.raises(BackendError, match="Copilot CLI failed"):
        backend.answer_question(
            repo_root=Path("."),
            query="test question",
            requested_category="dailyRoutine",
            profile_markdown="profile",
            related_notes="notes",
        )


def test_copilot_answer_question_parses_prompt_mode_jsonl(monkeypatch) -> None:
    backend = CopilotCliBackend("copilot")

    response_json = (
        '{"title":"Milk check","category":"Food & Liquids","terminal_summary":["Line 1"],'
        '"short_answer":"short","detailed_answer":"details","reasoning":["r1"],'
        '"references":[],"follow_up_questions":[],"profile_updates":[],"conflicts_or_gaps":[]}'
    )
    jsonl_stdout = "\n".join(
        [
            '{"type":"assistant.turn_start","data":{}}',
            '{"type":"assistant.message","data":{"content":' + json.dumps(response_json) + '}}',
            '{"type":"result","exitCode":0}',
        ]
    )

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["copilot"], returncode=0, stdout=jsonl_stdout, stderr="")

    monkeypatch.setattr("eagle_optimize.copilot_bridge.subprocess.run", fake_run)

    payload = backend.answer_question(
        repo_root=Path("."),
        query="test question",
        requested_category="dailyRoutine",
        profile_markdown="profile",
        related_notes="notes",
    )

    assert payload["title"] == "Milk check"
    assert payload["category"] == "Food & Liquids"
