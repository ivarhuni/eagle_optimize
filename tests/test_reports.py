from eagle_optimize.reports import guess_category_folder, render_current_profile_markdown


def test_guess_category_folder_prefers_drugs_keywords() -> None:
    assert guess_category_folder("What should I know about my ADHD medication discussion?") == "drugsSupplements"


def test_render_current_profile_markdown_contains_sections() -> None:
    markdown = render_current_profile_markdown({"age": "34"}, "2026-03-23T15:30:00")
    assert "# Current Profile" in markdown
    assert "Core profile" in markdown