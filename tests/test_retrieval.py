from pathlib import Path

from eagle_optimize.retrieval import (
    RetrievalResult,
    render_context_bundle,
    search_notes,
    tokenize,
)


def _setup_repo(tmp_path: Path) -> Path:
    """Create a minimal repo layout with some markdown files for testing."""
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    food = tmp_path / "optimizations" / "foodLiquids"
    food.mkdir(parents=True)
    routine = tmp_path / "optimizations" / "dailyRoutine"
    routine.mkdir(parents=True)

    (profiles / "current_profile.md").write_text(
        "# Current Profile\n- age: 30\n- goals: energy and focus\n",
        encoding="utf-8",
    )
    (food / "milk_tolerance_report.md").write_text(
        "# Milk Tolerance\nMilk contains lactose and protein. Dairy can cause digestive issues.\n",
        encoding="utf-8",
    )
    (food / "hydration_report.md").write_text(
        "# Hydration\nDrink water regularly. Avoid excess caffeine.\n",
        encoding="utf-8",
    )
    (routine / "morning_routine_report.md").write_text(
        "# Morning Routine\nWake up early. Exercise and eat protein for breakfast.\n",
        encoding="utf-8",
    )
    return tmp_path


def test_search_notes_returns_matching_files(tmp_path) -> None:
    repo = _setup_repo(tmp_path)
    results = search_notes(repo, "milk protein", limit=5)

    assert len(results) >= 1
    paths = [r.path.name for r in results]
    assert "milk_tolerance_report.md" in paths


def test_search_notes_filename_match_boosts_score(tmp_path) -> None:
    repo = _setup_repo(tmp_path)
    results = search_notes(repo, "milk", limit=5)

    top = results[0]
    assert top.path.name == "milk_tolerance_report.md"
    # Filename bonus (+4) should make this score higher than body-only matches
    assert top.score >= 5


def test_search_notes_no_matches_returns_empty(tmp_path) -> None:
    repo = _setup_repo(tmp_path)
    results = search_notes(repo, "xylophone quantum", limit=5)

    assert results == []


def test_search_notes_respects_limit(tmp_path) -> None:
    repo = _setup_repo(tmp_path)
    results = search_notes(repo, "protein", limit=1)

    assert len(results) == 1


def test_render_context_bundle_formats_results(tmp_path) -> None:
    repo = _setup_repo(tmp_path)
    results = [
        RetrievalResult(path=tmp_path / "profiles" / "current_profile.md", score=5, excerpt="age: 30"),
        RetrievalResult(path=tmp_path / "optimizations" / "foodLiquids" / "milk_tolerance_report.md", score=3, excerpt="Milk contains lactose"),
    ]

    output = render_context_bundle(repo, results)

    assert "Path:" in output
    assert "Score: 5" in output
    assert "Score: 3" in output
    assert "---" in output
    assert "age: 30" in output
    assert "Milk contains lactose" in output


def test_render_context_bundle_empty() -> None:
    output = render_context_bundle(Path("/fake"), [])
    assert output == "No directly relevant prior notes were found."


def test_tokenize_filters_short_tokens() -> None:
    tokens = tokenize("I am a big dog")
    assert "big" in tokens
    assert "dog" in tokens
    assert "am" not in tokens
    assert "a" not in tokens


def test_tokenize_lowercases_and_splits_punctuation() -> None:
    tokens = tokenize("Hello-World! Test123")
    assert tokens == ["hello", "world", "test123"]
