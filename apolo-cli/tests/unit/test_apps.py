from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import Any
from unittest import mock

from apolo_sdk import App, AppEvent, AppEventResource, AppValue
from apolo_sdk._apps import Apps

from .factories import _app_factory

_RunCli = Any


@contextmanager
def mock_apps_list(apps: list[App]) -> Iterator[None]:
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

        async def install(**kwargs: Any) -> App:
            return _app_factory()

        mocked.side_effect = install
        yield


@contextmanager
def mock_apps_configure() -> Iterator[None]:
    """Context manager to mock the Apps.install method."""
    with mock.patch.object(Apps, "configure") as mocked:

        async def configure(**kwargs: Any) -> App:
            return _app_factory(state="queued")

        mocked.side_effect = configure
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
        _app_factory(),
        _app_factory(
            id="app-456", name="test-app-2", display_name="Test App 2", state="errored"
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
        _app_factory(),
        _app_factory(
            id="app-456", name="test-app-2", display_name="Test App 2", state="errored"
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


def test_app_update(run_cli: _RunCli, tmp_path: Any) -> None:
    """Test the app update command."""
    app_yaml = tmp_path / "app.yaml"
    app_yaml.write_text(
        """
    display_name: New app name
    input: {}
    """
    )

    with mock_apps_configure():
        capture = run_cli(["app", "configure", "app-id-123", "-f", str(app_yaml)])

    assert not capture.err
    assert "configured using" in capture.out
    assert capture.code == 0


def test_app_uninstall(run_cli: _RunCli) -> None:
    """Test the app uninstall command."""
    app_id = "app-123"

    with mock_apps_uninstall():
        capture = run_cli(["app", "uninstall", app_id])

    assert not capture.err
    assert f"App {app_id} uninstalled" in capture.out
    assert capture.code == 0


def test_app_uninstall_with_force(run_cli: _RunCli) -> None:
    """Test the app uninstall command with --force flag."""
    app_id = "app-123"

    with mock_apps_uninstall():
        capture = run_cli(["app", "uninstall", "--force", app_id])

    assert not capture.err
    assert f"App {app_id} uninstalled" in capture.out
    assert capture.code == 0


@contextmanager
def mock_apps_get_values(values: list[AppValue]) -> Iterator[None]:
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
            instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
            type="dict",
            path="chat_internal_api",
            value={"url": "http://internal-api:8080"},
        ),
        AppValue(
            instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
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
            instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
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
            instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
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
            instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
            type="dict",
            path="chat_internal_api",
            value={"url": "http://internal-api:8080"},
        ),
        AppValue(
            instance_id="1d9a7843-75f6-4624-973d-6bdd57b1f628",
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


@contextmanager
def mock_apps_get_events(events: list[AppEvent]) -> Iterator[None]:
    """Context manager to mock the Apps.get_events method."""
    with mock.patch.object(Apps, "get_events") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs: Any) -> AsyncIterator[AsyncIterator[AppEvent]]:
            async def async_iterator() -> AsyncIterator[AppEvent]:
                for event in events:
                    yield event

            yield async_iterator()

        mocked.side_effect = async_cm
        yield


def test_app_get_status(run_cli: _RunCli) -> None:
    """Test the app get-status command."""
    events = [
        AppEvent(
            created_at=datetime.fromisoformat("2025-11-27T12:23:47.555539"),
            state="healthy",
            reason="Autoupdated",
            message=None,
            resources=[
                AppEventResource(
                    kind="Deployment",
                    name="test-deployment",
                    uid="abc-123",
                    health_status="Healthy",
                    health_message=None,
                ),
            ],
        ),
        AppEvent(
            created_at=datetime.fromisoformat("2025-11-27T12:22:17.441916"),
            state="progressing",
            reason="Autoupdated",
            message="Deployment is in progress",
            resources=[],
        ),
    ]

    with mock_apps_get_events(events):
        capture = run_cli(["app", "get-status", "app-123"])

    assert not capture.err
    assert "Event @" in capture.out
    assert "healthy" in capture.out
    assert "Autoupdated" in capture.out
    assert "progressing" in capture.out
    assert capture.code == 0


def test_app_get_status_no_events(run_cli: _RunCli) -> None:
    """Test the app get-status command when no events are returned."""
    with mock_apps_get_events([]):
        capture = run_cli(["app", "get-status", "app-123"])

    assert not capture.err
    assert "No events found." in capture.out
    assert capture.code == 0


def test_app_get_status_json_output(run_cli: _RunCli) -> None:
    """Test the app get-status command with JSON output."""
    events = [
        AppEvent(
            created_at=datetime.fromisoformat("2025-11-27T12:23:47.555539"),
            state="healthy",
            reason="Autoupdated",
            message=None,
            resources=[
                AppEventResource(
                    kind="Deployment",
                    name="test-deployment",
                    uid="abc-123",
                    health_status="Healthy",
                    health_message=None,
                ),
            ],
        ),
    ]

    with mock_apps_get_events(events):
        capture = run_cli(["app", "get-status", "app-123", "--output", "json"])

    assert not capture.err
    assert '"state": "healthy"' in capture.out
    assert '"reason": "Autoupdated"' in capture.out
    assert '"kind": "Deployment"' in capture.out
    assert '"name": "test-deployment"' in capture.out
    assert '"health_status": "Healthy"' in capture.out
    assert '"total": 1' in capture.out
    assert capture.code == 0


def test_app_get_status_quiet_mode(run_cli: _RunCli) -> None:
    """Test the app get-status command in quiet mode."""
    events = [
        AppEvent(
            created_at=datetime.fromisoformat("2025-11-27T12:23:47.555539"),
            state="healthy",
            reason="Autoupdated",
            message=None,
            resources=[],
        ),
    ]

    with mock_apps_get_events(events):
        capture = run_cli(["-q", "app", "get-status", "app-123"])

    assert not capture.err
    assert "healthy" in capture.out
    assert "Autoupdated" in capture.out
    assert capture.code == 0


def test_app_get_status_with_message(run_cli: _RunCli) -> None:
    """Test the app get-status command with event message."""
    events = [
        AppEvent(
            created_at=datetime.fromisoformat("2025-11-27T12:23:47.555539"),
            state="degraded",
            reason="DeploymentFailed",
            message="Deployment exceeded its progress deadline",
            resources=[],
        ),
    ]

    with mock_apps_get_events(events):
        capture = run_cli(["app", "get-status", "app-123"])

    assert not capture.err
    assert "degraded" in capture.out
    assert "DeploymentFailed" in capture.out
    assert "Deployment exceeded its progress deadline" in capture.out
    assert capture.code == 0
