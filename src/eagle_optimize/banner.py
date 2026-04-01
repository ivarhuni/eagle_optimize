from __future__ import annotations

import random
import sys
from typing import Optional, TextIO, Tuple


_ANSI_256_LINE_COLORS: Tuple[int, ...] = (130, 130, 137, 137, 180, 223, 223, 223, 180, 137, 130, 81)

_EYE_VARIANTS: Tuple[str, ...] = (
    "o o",
    "O O",
    "0 0",
    "- -",
    "^ ^",
    "* *",
    "x x",
    "@ @",
    "u u",
    "v v",
)

_CREST_VARIANTS: Tuple[str, ...] = ("^", "~", "*", "+", "x", "o", "v", "=", "#", "-")


def _build_ascii_art(eyes: str, crest: str) -> str:
    lines = (
        "                     .-.",
        "                    /___\\",
        f"               .--./{eyes}\\.--.",
        f"              /`-._\\_{crest}_/_.-'\\",
        "              \\_   /`'\\   _/",
        "             .' `-`\\_/`-` '.",
        "            /  .--.   .--.  \\",
        "           /  /    \\_/    \\  \\",
        "          /__/|           |\\__\\",
        "             /_/\\       /\\_\\",
        "                 \\__ __/",
        "                   V V",
    )
    return "\n".join(lines)


def _build_ascii_art_library() -> Tuple[str, ...]:
    arts = tuple(_build_ascii_art(eyes, crest) for eyes in _EYE_VARIANTS for crest in _CREST_VARIANTS)
    if len(arts) != 100:
        raise ValueError(f"Expected exactly 100 ASCII arts, got {len(arts)}")
    return arts


_ASCII_ART_LIBRARY: Tuple[str, ...] = _build_ascii_art_library()


def _choose_random_art_lines() -> Tuple[str, ...]:
    return tuple(random.choice(_ASCII_ART_LIBRARY).splitlines())


def _line_color(index: int) -> int:
    return _ANSI_256_LINE_COLORS[index % len(_ANSI_256_LINE_COLORS)]


def _colorize(text: str, color_code: int, use_color: bool) -> str:
    if not use_color:
        return text
    return f"\033[38;5;{color_code}m{text}\033[0m"


def render_startup_banner(color: bool = True) -> str:
    lines = _choose_random_art_lines()
    return "\n".join(_colorize(line, _line_color(index), color) for index, line in enumerate(lines))


def should_render_startup_banner(stream: Optional[TextIO] = None) -> bool:
    output = stream or sys.stdout
    isatty = getattr(output, "isatty", None)
    return bool(callable(isatty) and isatty())