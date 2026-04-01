import io
import time

import pytest

from eagle_optimize.terminal_loader import FunkyTerminalLoader, run_with_funky_loader


class TtyBuffer(io.StringIO):
    def isatty(self) -> bool:
        return True


def test_funky_loader_renders_status_in_tty_stream() -> None:
    stream = TtyBuffer()
    loader = FunkyTerminalLoader(
        message="Synthesizing your optimization answer",
        stream=stream,
        interval=0.01,
        enabled=True,
    )

    loader.start()
    time.sleep(0.05)
    loader.stop(succeeded=True)

    output = stream.getvalue()
    assert "Synthesizing your optimization answer" in output
    assert "[DONE]" in output


def test_funky_loader_context_marks_failure_on_exception() -> None:
    stream = TtyBuffer()

    with pytest.raises(RuntimeError):
        with run_with_funky_loader(
            message="Synthesizing your optimization answer",
            enabled=True,
            stream=stream,
        ):
            raise RuntimeError("backend error")

    assert "[FAIL]" in stream.getvalue()


def test_funky_loader_no_output_when_stream_is_not_tty() -> None:
    stream = io.StringIO()

    with run_with_funky_loader(
        message="Synthesizing your optimization answer",
        enabled=True,
        stream=stream,
    ):
        pass

    assert stream.getvalue() == ""
