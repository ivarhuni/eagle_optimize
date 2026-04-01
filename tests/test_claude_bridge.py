import json
import subprocess
from pathlib import Path

import pytest

from eagle_optimize.claude_bridge import BackendError, ClaudeCliBackend, RESPONSE_SCHEMA


def _make_structured_output(**overrides):
    base = {
        "title": "Test Title",
        "category": "Daily Routine",
        "terminal_summary": ["Summary line 1"],
        "short_answer": "Short answer text",
        "detailed_answer": "Detailed answer text",
        "reasoning": ["Reasoning 1"],
        "references": [],
        "follow_up_questions": [],
        "profile_updates": [],
        "conflicts_or_gaps": [],
    }
    base.update(overrides)
    return base


def _make_envelope(structured_output=None, is_error=False, subtype="success", result_text=""):
    return {
        "type": "result",
        "subtype": subtype,
        "is_error": is_error,
        "result": result_text,
        "structured_output": structured_output,
        "duration_ms": 1234,
        "session_id": "test-session-id",
    }


_CALL_KWARGS = dict(
    repo_root=Path("/fake/repo"),
    query="Is milk good for me?",
    requested_category="foodLiquids",
    profile_markdown="# Profile\n- age: 34",
    related_notes="No directly relevant prior notes were found.",
)


# --- doctor tests ---


def test_doctor_available_and_authenticated(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")

    def fake_run(args, **_kwargs):
        if args == ["claude", "-v"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="1.0.32", stderr="")
        if args == ["claude", "auth", "status"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="Authenticated as user@example.com", stderr="")
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr("eagle_optimize.claude_bridge.shutil.which", lambda _exe: "/usr/local/bin/claude")
    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    result = backend.doctor()

    assert result.available is True
    assert result.authenticated is True
    assert result.version == "1.0.32"
    assert "Authenticated" in result.auth_detail


def test_doctor_command_not_found(monkeypatch) -> None:
    backend = ClaudeCliBackend("/nonexistent/claude")

    monkeypatch.setattr("eagle_optimize.claude_bridge.shutil.which", lambda _exe: None)

    result = backend.doctor()

    assert result.available is False
    assert result.authenticated is False
    assert result.auth_detail == "Command not found."


def test_doctor_available_but_not_authenticated(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")

    def fake_run(args, **_kwargs):
        if args == ["claude", "-v"]:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="1.0.32", stderr="")
        if args == ["claude", "auth", "status"]:
            return subprocess.CompletedProcess(args=args, returncode=1, stdout="", stderr="Not authenticated. Run `claude auth login`.")
        raise AssertionError(f"Unexpected command: {args}")

    monkeypatch.setattr("eagle_optimize.claude_bridge.shutil.which", lambda _exe: "/usr/local/bin/claude")
    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    result = backend.doctor()

    assert result.available is True
    assert result.authenticated is False
    assert "Not authenticated" in result.auth_detail


# --- answer_question tests ---


def test_answer_question_success_parses_structured_output(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")
    expected = _make_structured_output()
    envelope = _make_envelope(structured_output=expected)

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["claude"], returncode=0, stdout=json.dumps(envelope), stderr="")

    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    result = backend.answer_question(**_CALL_KWARGS)

    assert result["title"] == "Test Title"
    assert result["category"] == "Daily Routine"
    assert result["short_answer"] == "Short answer text"
    assert result["terminal_summary"] == ["Summary line 1"]


def test_answer_question_command_includes_output_format_json(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")
    captured_args = {}

    def fake_run(args, **kwargs):
        captured_args["args"] = args
        captured_args["kwargs"] = kwargs
        envelope = _make_envelope(structured_output=_make_structured_output())
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps(envelope), stderr="")

    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    backend.answer_question(**_CALL_KWARGS)

    args = captured_args["args"]
    assert "--output-format" in args
    fmt_index = args.index("--output-format")
    assert args[fmt_index + 1] == "json"
    assert "--json-schema" in args
    assert "--no-session-persistence" in args


def test_answer_question_passes_prompt_via_stdin(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")
    captured_kwargs = {}

    def fake_run(args, **kwargs):
        captured_kwargs.update(kwargs)
        envelope = _make_envelope(structured_output=_make_structured_output())
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=json.dumps(envelope), stderr="")

    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    backend.answer_question(**_CALL_KWARGS)

    stdin_input = captured_kwargs.get("input", "")
    assert "Is milk good for me?" in stdin_input
    assert "# Profile" in stdin_input


def test_answer_question_nonzero_exit_raises_backend_error(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["claude"], returncode=1, stdout="", stderr="Rate limit exceeded")

    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    with pytest.raises(BackendError, match="Rate limit exceeded"):
        backend.answer_question(**_CALL_KWARGS)


def test_answer_question_missing_structured_output_raises(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")
    envelope = _make_envelope(structured_output=None)

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["claude"], returncode=0, stdout=json.dumps(envelope), stderr="")

    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    with pytest.raises(BackendError, match="missing structured_output"):
        backend.answer_question(**_CALL_KWARGS)


def test_answer_question_invalid_json_raises(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["claude"], returncode=0, stdout="not valid json", stderr="")

    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    with pytest.raises(BackendError, match="invalid JSON"):
        backend.answer_question(**_CALL_KWARGS)


def test_answer_question_is_error_raises(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")
    envelope = _make_envelope(is_error=True, subtype="error", result_text="Tool execution failed")

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["claude"], returncode=0, stdout=json.dumps(envelope), stderr="")

    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    with pytest.raises(BackendError, match="Claude error.*Tool execution failed"):
        backend.answer_question(**_CALL_KWARGS)


def test_answer_question_unexpected_subtype_raises(monkeypatch) -> None:
    backend = ClaudeCliBackend("claude")
    envelope = _make_envelope(subtype="cancelled", structured_output=None)

    def fake_run(*_args, **_kwargs):
        return subprocess.CompletedProcess(args=["claude"], returncode=0, stdout=json.dumps(envelope), stderr="")

    monkeypatch.setattr("eagle_optimize.claude_bridge.subprocess.run", fake_run)

    with pytest.raises(BackendError, match="unexpected subtype.*cancelled"):
        backend.answer_question(**_CALL_KWARGS)


def test_build_prompt_contains_expected_sections() -> None:
    prompt = ClaudeCliBackend._build_prompt(
        query="Should I drink milk?",
        requested_category="foodLiquids",
        profile_markdown="# Profile\n- age: 30",
        related_notes="No notes.",
    )

    assert "Should I drink milk?" in prompt
    assert "foodLiquids" in prompt
    assert "# Profile" in prompt
    assert "No notes." in prompt
    assert "personalized optimization note" in prompt
    assert "profile_updates" in prompt
    assert "conflicts_or_gaps" in prompt
    assert "prescription medications" in prompt


# --- live smoke test ---


@pytest.mark.slow
def test_live_round_trip(tmp_path) -> None:
    """Actually calls the Claude CLI. Requires `claude` to be installed and authenticated.

    Run with: uv run --extra dev pytest -m slow
    """
    import shutil

    if not shutil.which("claude"):
        pytest.skip("Claude CLI not available")

    backend = ClaudeCliBackend("claude")
    doctor_result = backend.doctor()
    if not doctor_result.authenticated:
        pytest.skip("Claude CLI not authenticated")

    result = backend.answer_question(
        repo_root=tmp_path,
        query="What is one simple morning habit for energy?",
        requested_category="dailyRoutine",
        profile_markdown="# Profile\n- age: 30\n- goals: energy",
        related_notes="No directly relevant prior notes were found.",
    )

    assert isinstance(result, dict)
    assert "title" in result
    assert "short_answer" in result
    assert "detailed_answer" in result
    assert "terminal_summary" in result
    assert len(result["terminal_summary"]) >= 1
