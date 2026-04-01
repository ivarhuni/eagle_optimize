from __future__ import annotations

from contextlib import contextmanager
import sys
import threading
from typing import Iterator, Optional, TextIO


class FunkyTerminalLoader:
    _FRAMES = (
        "[=      ]",
        "[==     ]",
        "[===    ]",
        "[ ====  ]",
        "[  ==== ]",
        "[   === ]",
        "[    == ]",
        "[     = ]",
    )
    _TRAIL = (
        "warming engines",
        "cross-linking notes",
        "tuning context",
        "brewing signal",
    )
    _COLORS = (39, 45, 81, 118, 214, 202, 198, 135)

    def __init__(
        self,
        message: str,
        stream: Optional[TextIO] = None,
        interval: float = 0.08,
        enabled: bool = True,
    ) -> None:
        self.message = message
        self.stream = stream or sys.stderr
        self.interval = max(interval, 0.02)
        is_tty = bool(getattr(self.stream, "isatty", lambda: False)())
        self.enabled = enabled and is_tty
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not self.enabled or self._thread is not None:
            return
        self._thread = threading.Thread(target=self._spin, name="eagle-optimize-loader", daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        index = 0
        while not self._stop_event.wait(self.interval):
            frame = self._FRAMES[index % len(self._FRAMES)]
            trail = self._TRAIL[index % len(self._TRAIL)]
            color = self._COLORS[index % len(self._COLORS)]
            self.stream.write(f"\r\033[38;5;{color}m{frame}\033[0m {self.message} :: {trail}")
            self.stream.flush()
            index += 1

    def stop(self, succeeded: bool = True) -> None:
        if not self.enabled:
            return
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self.interval * 4)

        status = "DONE" if succeeded else "FAIL"
        color_code = "32" if succeeded else "31"
        self.stream.write(f"\r\033[2K\033[1;{color_code}m[{status}]\033[0m {self.message}\n")
        self.stream.flush()


@contextmanager
def run_with_funky_loader(
    message: str,
    enabled: bool = True,
    stream: Optional[TextIO] = None,
) -> Iterator[None]:
    loader = FunkyTerminalLoader(message=message, stream=stream, enabled=enabled)
    loader.start()
    succeeded = False
    try:
        yield
        succeeded = True
    finally:
        loader.stop(succeeded=succeeded)
