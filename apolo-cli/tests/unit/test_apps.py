from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Iterator, List
from unittest import mock

from apolo_sdk import App, AppValue
from apolo_sdk._apps import Apps

_RunCli = Any


@contextmanager
def mock_apps_list(apps: List[App]) -> Iterator[None]:
    """Context manager to mock the Apps.list method."""
    with mock.patch.object(Apps, "list") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs: Any) -> AsyncIterator[AsyncIterator[App]]:
            async def async_iterator() -> AsyncIterator[App]:
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


@contextmanager
def mock_apps_get_values(values: List[AppValue]) -> Iterator[None]:
    """Context manager to mock the Apps.get_values method."""
    with mock.patch.object(Apps, "get_values") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs: Any) -> AsyncIterator[AsyncIterator[AppValue]]:
            async def async_iterator() -> AsyncIterator[AppValue]:
                for value in values:
                    yield value

            yield async_iterator()

        mocked.side_effect = async_cm
        yield


def test_app_get_values_with_values(run_cli: _RunCli) -> None:
    """Test the app get-values command when values are returned."""
    values = [
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
    ]

    with mock_apps_get_values(values):
        capture = run_cli(["app", "get-values"])

    assert not capture.err
    assert "1d9a7843-75f6-4624-973d-6bdd57b1f628" in capture.out
    assert "dict" in capture.out
    assert "chat_internal_api" in capture.out
    assert "chat_external_api" in capture.out
    assert capture.code == 0


def test_app_get_values_with_app_id(run_cli: _RunCli) -> None:
    """Test the app get-values command with app ID filter."""
    values = [
        AppValue(
            app_instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
            type="dict",
            path="chat_internal_api",
            value={"url": "http://internal-api:8080"},
        ),
    ]

    with mock_apps_get_values(values):
        capture = run_cli(["app", "get-values", "1d9a7843-75f6-4624-973d-6bdd57b1f628"])

    assert not capture.err
    assert "1d9a7843-75f6-4624-973d-6bdd57b1f628" in capture.out
    assert capture.code == 0


def test_app_get_values_with_type_filter(run_cli: _RunCli) -> None:
    """Test the app get-values command with type filter."""
    values = [
        AppValue(
            app_instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
            type="dict",
            path="chat_internal_api",
            value={"url": "http://internal-api:8080"},
        ),
    ]

    with mock_apps_get_values(values):
        capture = run_cli(["app", "get-values", "-t", "dict"])

    assert not capture.err
    assert "1d9a7843-75f6-4624-973d-6bdd57b1f628" in capture.out
    assert "dict" in capture.out
    assert capture.code == 0


def test_app_get_values_no_values(run_cli: _RunCli) -> None:
    """Test the app get-values command when no values are returned."""
    with mock_apps_get_values([]):
        capture = run_cli(["app", "get-values"])

    assert not capture.err
    assert "No app values found." in capture.out
    assert capture.code == 0


def test_app_get_values_quiet_mode(run_cli: _RunCli) -> None:
    """Test the app get-values command in quiet mode."""
    values = [
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
    ]

    with mock_apps_get_values(values):
        capture = run_cli(["-q", "app", "get-values"])

    assert not capture.err
    internal_api_value = "1d9a7843-75f6-4624-973d-6bdd57b1f628:dict:chat_internal_api:"
    internal_api_value += '{"url": "http://internal-api:8080"}'
    assert internal_api_value in capture.out

    external_api_value = "1d9a7843-75f6-4624-973d-6bdd57b1f628:dict:chat_external_api:"
    external_api_value += '{"url": "https://api.example.com"}'
    assert external_api_value in capture.out
    assert capture.code == 0


@contextmanager
def mock_apps_logs() -> Iterator[None]:
    """Context manager to mock the Apps.logs method."""
    with mock.patch.object(Apps, "logs") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs: Any) -> AsyncIterator[AsyncIterator[bytes]]:
            async def async_iterator() -> AsyncIterator[bytes]:
                logs = [
                    b"Starting app...\n",
                    b"App initialized\n",
                    b"App ready\n",
                ]
                for log in logs:
                    yield log

            yield async_iterator()

        mocked.side_effect = async_cm
        yield


def test_app_logs(run_cli: _RunCli) -> None:
    """Test the app logs command."""
    app_id = "app-123"

    with mock_apps_logs():
        capture = run_cli(["app", "logs", app_id])

    assert not capture.err
    assert "Starting app..." in capture.out
    assert "App initialized" in capture.out
    assert "App ready" in capture.out
    assert capture.code == 0


def test_app_logs_with_since(run_cli: _RunCli) -> None:
    """Test the app logs command with since parameter."""
    app_id = "app-123"

    with mock_apps_logs():
        capture = run_cli(["app", "logs", app_id, "--since", "1h"])

    assert not capture.err
    assert "Starting app..." in capture.out
    assert capture.code == 0


def test_app_logs_with_timestamps(run_cli: _RunCli) -> None:
    """Test the app logs command with timestamps."""
    app_id = "app-123"

    with mock_apps_logs():
        capture = run_cli(["app", "logs", app_id, "--timestamps"])

    assert not capture.err
    assert "Starting app..." in capture.out
    assert capture.code == 0
