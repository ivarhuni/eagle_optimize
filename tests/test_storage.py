from eagle_optimize.storage import camel_case_slug, normalize_category_input


def test_camel_case_slug() -> None:
    assert camel_case_slug("Is milk good for me?") == "isMilkGoodForMe"


def test_normalize_category_input_supports_display_and_folder_names() -> None:
    assert normalize_category_input("Food & Liquids") == "foodLiquids"
    assert normalize_category_input("drugsSupplements") == "drugsSupplements"