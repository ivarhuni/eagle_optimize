from __future__ import annotations

import sys
from typing import Optional, TextIO


_BANNER_LINES: tuple[tuple[Optional[int], str], ...] = (
    (130, "                .-~~~~~~~~~~-."),
    (130, "            .-~~  .::::::::.  ~~-."),
    (137, "         .-~    .::::'  '::::.    ~-."),
    (137, "       .'     .::::' /\\   '::::.     '."),
    (180, "      /      .:::'  /  \\    ':::.      \\ "),
    (223, "     ;      .:::'  | () |    ':::.      ;"),
    (223, "     |      :::    | __ |      :::      |"),
    (223, "     |      :::    |/  \\|      :::      |"),
    (180, "     ;      ':::.   \\__/     .:::'      ;"),
    (137, "      \\       '::::..____..::::'       /"),
    (130, "       '.         .-____-.         .'"),
    (130, "         '-.___.-'  /||\\  '-.___.-'"),
    (81, "           _/  _   _/ || \\_   _  \\ "),
    (214, "         .' /\\_/\\.'   ||   './\\_/\\ '."),
    (198, "        /__/   /_/    ||    \\_\\   \\__\\"),
)


def _colorize(text: str, color_code: Optional[int], use_color: bool) -> str:
    if not use_color or color_code is None:
        return text
    return f"\033[38;5;{color_code}m{text}\033[0m"


def render_startup_banner(color: bool = True) -> str:
    return "\n".join(_colorize(line, color_code, color) for color_code, line in _BANNER_LINES)


def should_render_startup_banner(stream: Optional[TextIO] = None) -> bool:
    output = stream or sys.stdout
    isatty = getattr(output, "isatty", None)
    return bool(callable(isatty) and isatty())