from collections.abc import Iterator
from pathlib import Path

import aiohttp
import pytest

from apolo_cli.root import Root
from apolo_cli.utils import Command, Context


@pytest.fixture
def root_uninitialized() -> Iterator[Root]:
    async def cmd() -> None:
        pass

    root = Root(
        color=False,
        tty=False,
        disable_pypi_version_check=False,
        network_timeout=60,
        config_path=Path("~/.apolo"),
        verbosity=0,
        trace=False,
        trace_hide_token=True,
        force_trace_all=False,
        command_path="",
        command_params=[],
        skip_gmp_stats=True,
        show_traceback=False,
        iso_datetime_format=False,
        ctx=Context(Command(cmd, name="")),
    )
    yield root
    root.close()


def test_timeout(root_uninitialized: Root) -> None:
    assert root_uninitialized.timeout == aiohttp.ClientTimeout(None, None, 60, 60)


class TestTokenSanitization:
    @pytest.mark.parametrize("auth", ["Bearer", "Basic", "Digest", "Mutual"])
    def test_sanitize_header_value_single_token(
        self, root_uninitialized: Root, auth: str
    ) -> None:
        line = f"{auth} eyJhbGciOiJI.eyJzdW0NTY3.SfKxwRJ_SsM"
        expected = f"{auth} eyJhb<hidden 26 chars>J_SsM"
        line_safe = root_uninitialized._sanitize_header_value(line)
        assert line_safe == expected

    @pytest.mark.parametrize("auth", ["Bearer", "Basic", "Digest", "Mutual"])
    def test_sanitize_header_value_many_tokens(
        self, root_uninitialized: Root, auth: str
    ) -> None:
        num = 10
        line = f"{auth} eyJhbGcOiJI.eyJzdTY3.SfKxwRJ_SsM " * num
        expected = f"{auth} eyJhb<hidden 22 chars>J_SsM " * num
        line_safe = root_uninitialized._sanitize_header_value(line)
        assert line_safe == expected

    @pytest.mark.parametrize("auth", ["Bearer", "Basic", "Digest", "Mutual"])
    def test_sanitize_header_value_not_a_token(
        self, root_uninitialized: Root, auth: str
    ) -> None:
        line = f"{auth} not_a_jwt"
        line_safe = root_uninitialized._sanitize_header_value(line)
        assert line_safe == f"{auth} not_a_jwt"

    def test_sanitize_token_replaced_overall(self, root_uninitialized: Root) -> None:
        token = "a.b.c"
        line_safe = root_uninitialized._sanitize_token(token)
        assert line_safe == "<hidden 5 chars>"
