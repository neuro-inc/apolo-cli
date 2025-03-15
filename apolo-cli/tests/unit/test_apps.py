from typing import Any, AsyncIterator, Generic, List, TypeVar

import pytest
from click.testing import CliRunner

from apolo_sdk import App

from apolo_cli.main import cli

T = TypeVar("T")


class MockAsyncContext(Generic[T]):
    """Mock async context manager for testing SDK methods
    that return async iterators.
    """

    def __init__(self, items: List[T]) -> None:
        self.items = items

    async def __aenter__(self) -> AsyncIterator[T]:
        return self.mock_list_context()

    async def __aexit__(self, *args: Any) -> None:
        pass

    async def mock_list_context(self) -> AsyncIterator[T]:
        for item in self.items:
            yield item


@pytest.fixture
def mock_apps() -> List[App]:
    """Return a list of mock App objects for testing."""
    return [
        App(
            id="app-123",
            name="test-app-1",
            display_name="Test App 1",
            template_name="test-template",
            template_version="1.0",
            project_name="test-project",
            org_name="test-org",
            state="running",
        ),
        App(
            id="app-456",
            name="test-app-2",
            display_name="Test App 2",
            template_name="test-template",
            template_version="1.0",
            project_name="test-project",
            org_name="test-org",
            state="errored",
        ),
    ]


class TestAppCommands:
    """Tests for app commands."""

    def test_ls_command_with_apps(
        self,
        mock_apps: List[App],
        monkeypatch: Any,
    ) -> None:
        """Test the ls command when apps are returned."""

        # Mock the Apps.list method
        monkeypatch.setattr(
            "apolo_sdk._apps.Apps.list",
            lambda self, **kwargs: MockAsyncContext(mock_apps),
        )

        # Run the command
        runner = CliRunner()
        result = runner.invoke(cli, ["app", "ls"])

        # Check that the command was successful
        assert result.exit_code == 0

        # Check the output
        assert "app-123" in result.stdout
        assert "test-app-1" in result.stdout
        assert "Test App 1" in result.stdout
        assert "test-template" in result.stdout
        assert "1.0" in result.stdout
        assert "running" in result.stdout

    def test_ls_command_no_apps(
        self,
        monkeypatch: Any,
    ) -> None:
        """Test the ls command when no apps are returned."""

        # Mock the Apps.list method with empty list
        monkeypatch.setattr(
            "apolo_sdk._apps.Apps.list", lambda self, **kwargs: MockAsyncContext([])
        )

        # Run the command
        runner = CliRunner()
        result = runner.invoke(cli, ["app", "ls"])

        # Check that the command was successful
        assert result.exit_code == 0

        # Check the output
        assert "No apps found." in result.stdout

    def test_ls_command_quiet_mode(
        self,
        mock_apps: List[App],
        monkeypatch: Any,
    ) -> None:
        """Test the ls command in quiet mode."""

        # Mock the Apps.list method
        monkeypatch.setattr(
            "apolo_sdk._apps.Apps.list",
            lambda self, **kwargs: MockAsyncContext(mock_apps),
        )

        # Run the command
        runner = CliRunner()
        result = runner.invoke(cli, ["-q", "app", "ls"])

        # Check that the command was successful
        assert result.exit_code == 0

        # Check the output - in quiet mode, only IDs should be printed
        assert "app-123" in result.stdout, result.stdout
        assert "app-456" in result.stdout
        assert "Test App" not in result.stdout  # Display name should not be present
