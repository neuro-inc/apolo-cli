from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Iterator, List

import pytest

from apolo_sdk import AppValue
from apolo_sdk._apps import Apps

from apolo_cli.formatters.app_values import AppValuesFormatter, SimpleAppValuesFormatter


@contextmanager
def mock_apps_get_values(values: List[AppValue]) -> Iterator[None]:
    """Context manager to mock the Apps.get_values method."""
    from unittest import mock

    with mock.patch.object(Apps, "get_values") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs: Any) -> AsyncIterator[AsyncIterator[AppValue]]:
            async def async_iterator() -> AsyncIterator[AppValue]:
                for value in values:
                    yield value

            yield async_iterator()

        mocked.side_effect = async_cm
        yield


class TestAppValuesFormatter:
    @pytest.fixture
    def app_values(self) -> List[AppValue]:
        return [
            AppValue(
                app_instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
                type="dict",
                path="chat_internal_api",
                value={"url": "http://internal-api:8080"},
            ),
            AppValue(
                app_instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
                type="dict",
                path="chat_external_api",
                value={"url": "https://api.example.com"},
            ),
            AppValue(
                app_instance_id="a4723404-f5e2-48b5-b709-629754b5056f",
                type="string",
                path="api_endpoint",
                value="https://api.example.org/v1",
            ),
        ]

    def test_app_values_formatter(
        self, app_values: List[AppValue], rich_cmp: Any
    ) -> None:
        formatter = AppValuesFormatter()
        rich_cmp(formatter(app_values))

    def test_simple_app_values_formatter(
        self, app_values: List[AppValue], rich_cmp: Any
    ) -> None:
        formatter = SimpleAppValuesFormatter()
        rich_cmp(formatter(app_values))

    def test_app_values_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = AppValuesFormatter()
        rich_cmp(formatter([]))

    def test_simple_app_values_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = SimpleAppValuesFormatter()
        rich_cmp(formatter([]))
