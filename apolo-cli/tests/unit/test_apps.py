from contextlib import asynccontextmanager, contextmanager
from typing import Any, Iterator, List
from unittest import mock

from apolo_sdk import App
from apolo_sdk._apps import Apps

_RunCli = Any


@contextmanager
def mock_apps_list(apps: List[App]) -> Iterator[None]:
    """Context manager to mock the Apps.list method."""
    with mock.patch.object(Apps, "list") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs):
            async def async_iterator():
                for app in apps:
                    yield app

            yield async_iterator()

        mocked.side_effect = async_cm
        yield


@contextmanager
def mock_apps_install() -> Iterator[None]:
    """Context manager to mock the Apps.install method."""
    with mock.patch.object(Apps, "install") as mocked:

        async def install(**kwargs: Any) -> str:
            return "app-123"

        mocked.side_effect = install
        yield


@contextmanager
def mock_apps_uninstall() -> Iterator[None]:
    """Context manager to mock the Apps.uninstall method."""
    with mock.patch.object(Apps, "uninstall") as mocked:

        async def uninstall(**kwargs: Any) -> None:
            return None

        mocked.side_effect = uninstall
        yield


def test_app_ls_with_apps(run_cli: _RunCli) -> None:
    """Test the app ls command when apps are returned."""
    apps = [
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

    with mock_apps_list(apps):
        capture = run_cli(["app", "ls"])

    assert not capture.err
    assert "app-123" in capture.out
    assert "test-app-1" in capture.out
    assert "Test App 1" in capture.out
    assert "test-template" in capture.out
    assert "1.0" in capture.out
    assert "running" in capture.out
    assert capture.code == 0


def test_app_ls_no_apps(run_cli: _RunCli) -> None:
    """Test the app ls command when no apps are returned."""
    with mock_apps_list([]):
        capture = run_cli(["app", "ls"])

    assert not capture.err
    assert "No apps found." in capture.out
    assert capture.code == 0


def test_app_ls_quiet_mode(run_cli: _RunCli) -> None:
    """Test the app ls command in quiet mode."""
    apps = [
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

    with mock_apps_list(apps):
        capture = run_cli(["-q", "app", "ls"])

    assert not capture.err
    assert "app-123" in capture.out
    assert "app-456" in capture.out
    assert "Test App" not in capture.out  # Display name should not be present
    assert capture.code == 0


def test_app_install(run_cli: _RunCli, tmp_path: Any) -> None:
    """Test the app install command."""
    # Create a temporary app.yaml file
    app_yaml = tmp_path / "app.yaml"
    app_yaml.write_text(
        """
    template_name: test-template
    template_version: 1.0
    input: {}
    """
    )

    with mock_apps_install():
        capture = run_cli(["app", "install", "-f", str(app_yaml)])

    assert not capture.err
    assert "App installed" in capture.out
    assert capture.code == 0


def test_app_uninstall(run_cli: _RunCli) -> None:
    """Test the app uninstall command."""
    app_id = "app-123"

    with mock_apps_uninstall():
        capture = run_cli(["app", "uninstall", app_id])

    assert not capture.err
    assert f"App {app_id} uninstalled" in capture.out
    assert capture.code == 0
