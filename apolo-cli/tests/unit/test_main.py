from typing import Any


def test_help(run_cli: Any) -> None:
    capture = run_cli(["help"])

    assert capture.code == 0
    assert capture.err == ""
    assert capture.out.startswith("Usage: ")
    assert "[OPTIONS] COMMAND [ARGS]..." in capture.out
    assert "Commands:" in capture.out
    assert "help <command>" in capture.out
