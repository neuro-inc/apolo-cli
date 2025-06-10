import tempfile
from contextlib import contextmanager
from typing import Any, Iterator
from unittest import mock

from apolo_sdk import AppTemplate
from apolo_sdk._apps import Apps

_RunCli = Any


@contextmanager
def mock_apps_get_template(template: AppTemplate) -> Iterator[None]:
    """Context manager to mock the Apps.get_template method."""
    with mock.patch.object(Apps, "get_template") as mocked:

        async def async_func(**kwargs: Any) -> AppTemplate:
            return template

        mocked.side_effect = async_func
        yield


def test_app_template_get_unknown_output_format(run_cli: _RunCli) -> None:
    """Test the app_template get command with unknown output format."""
    template = AppTemplate(
        name="test-app",
        title="Test App",
        version="1.0.0",
        short_description="Test app",
        description="",
        tags=[],
        input={"type": "object", "properties": {"name": {"type": "string"}}},
    )

    with mock_apps_get_template(template):
        capture = run_cli(["app-template", "get", "test-app", "-o", "xml"])

    assert "Unknown output format: xml" in capture.out
    assert capture.code == 1


def test_app_template_get_json_format_no_input(run_cli: _RunCli) -> None:
    """Test the app_template get command with JSON format when no input schema."""
    template = AppTemplate(
        name="simple-app",
        title="Simple App",
        version="1.0.0",
        short_description="Simple app without input",
        description="",
        tags=[],
        input=None,
    )

    with mock_apps_get_template(template):
        capture = run_cli(["app-template", "get", "simple-app", "-o", "json"])

    assert not capture.err
    assert '"template_name": "simple-app"' in capture.out
    assert '"template_version": "1.0.0"' in capture.out
    assert '"input": {}' in capture.out
    assert capture.code == 0


def test_app_template_get_yaml_format_no_input(run_cli: _RunCli) -> None:
    """Test the app_template get command with YAML format when no input schema."""
    template = AppTemplate(
        name="simple-app",
        title="Simple App",
        version="1.0.0",
        short_description="Simple app without input",
        description="",
        tags=[],
        input=None,
    )

    with mock_apps_get_template(template):
        capture = run_cli(["app-template", "get", "simple-app", "-o", "yaml"])

    assert not capture.err
    assert "template_name: simple-app" in capture.out
    assert "template_version: 1.0.0" in capture.out
    assert "input: {}" in capture.out
    assert capture.code == 0


def test_app_template_get_quiet_mode(run_cli: _RunCli) -> None:
    """Test the app_template get command in quiet mode."""
    template = AppTemplate(
        name="test-app",
        title="Test App",
        version="1.0.0",
        short_description="Test app",
        description="",
        tags=[],
        input={"type": "object", "properties": {"name": {"type": "string"}}},
    )

    with mock_apps_get_template(template):
        capture = run_cli(["-q", "app-template", "get", "test-app"])

    assert not capture.err
    # In quiet mode, we should still see the output, just no status messages
    assert "template_name: test-app" in capture.out
    assert "template_version: 1.0.0" in capture.out
    assert capture.code == 0


def test_app_template_get_quiet_mode_with_file(run_cli: _RunCli) -> None:
    """Test the app_template get command in quiet mode with file output."""
    template = AppTemplate(
        name="test-app",
        title="Test App",
        version="1.0.0",
        short_description="Test app",
        description="",
        tags=[],
        input={"type": "object", "properties": {"name": {"type": "string"}}},
    )

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as tmp_file:
        temp_path = tmp_file.name

    try:
        with mock_apps_get_template(template):
            capture = run_cli(["-q", "app-template", "get", "test-app", "-f", temp_path])

        assert not capture.err
        # In quiet mode, should not see the "Template saved to" message
        assert "Template saved to" not in capture.out
        assert capture.code == 0

        # But file should still be created
        with open(temp_path) as f:
            content = f.read()
            assert "template_name: test-app" in content
    finally:
        import os

        if os.path.exists(temp_path):
            os.unlink(temp_path)


def test_app_template_ls_with_cluster_option(run_cli: _RunCli) -> None:
    """Test the app_template ls command with cluster option."""
    from apolo_sdk import AppTemplate
    from apolo_sdk._apps import Apps
    from contextlib import asynccontextmanager
    from typing import AsyncIterator

    templates = [
        AppTemplate(
            name="test-app",
            title="Test App",
            version="1.0.0",
            short_description="Test app",
            tags=[],
            input=None,
            description="",
        ),
    ]

    with mock.patch.object(Apps, "list_templates") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs: Any) -> AsyncIterator[AsyncIterator[AppTemplate]]:
            async def async_iterator() -> AsyncIterator[AppTemplate]:
                for template in templates:
                    yield template

            yield async_iterator()

        mocked.side_effect = async_cm

        with mock.patch("apolo_cli.click_types.CLUSTER.convert") as convert_mock:
            convert_mock.return_value = "test-cluster"

            capture = run_cli(["app-template", "ls", "--cluster", "test-cluster"])

    assert not capture.err
    assert "test-app" in capture.out
    assert capture.code == 0


def test_app_template_ls_with_org_and_project_options(run_cli: _RunCli) -> None:
    """Test the app_template ls command with org and project options."""
    from apolo_sdk import AppTemplate
    from apolo_sdk._apps import Apps
    from contextlib import asynccontextmanager
    from typing import AsyncIterator

    templates = [
        AppTemplate(
            name="org-app",
            title="Org App",
            version="1.0.0",
            short_description="Organization app",
            tags=["org"],
            input=None,
            description="",
        ),
    ]

    with mock.patch.object(Apps, "list_templates") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs: Any) -> AsyncIterator[AsyncIterator[AppTemplate]]:
            async def async_iterator() -> AsyncIterator[AppTemplate]:
                for template in templates:
                    yield template

            yield async_iterator()

        mocked.side_effect = async_cm

        with mock.patch("apolo_cli.click_types.ORG.convert") as org_convert_mock:
            org_convert_mock.return_value = "test-org"

            with mock.patch("apolo_cli.click_types.PROJECT.convert") as proj_convert_mock:
                proj_convert_mock.return_value = "test-project"

                capture = run_cli(
                    ["app-template", "ls", "--org", "test-org", "--project", "test-project"]
                )

    assert not capture.err
    assert "org-app" in capture.out
    assert capture.code == 0


def test_app_template_get_with_all_options(run_cli: _RunCli) -> None:
    """Test the app_template get command with all options."""
    template = AppTemplate(
        name="full-test",
        title="Full Test",
        version="3.0.0",
        short_description="Full test with all options",
        description="",
        tags=[],
        input={
            "type": "object",
            "properties": {"param1": {"type": "string", "default": "test"}},
        },
    )

    with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tmp_file:
        temp_path = tmp_file.name

    try:
        with mock_apps_get_template(template):
            with mock.patch("apolo_cli.click_types.CLUSTER.convert") as cluster_mock:
                cluster_mock.return_value = "test-cluster"

                with mock.patch("apolo_cli.click_types.ORG.convert") as org_mock:
                    org_mock.return_value = "test-org"

                    with mock.patch("apolo_cli.click_types.PROJECT.convert") as proj_mock:
                        proj_mock.return_value = "test-project"

                        capture = run_cli(
                            [
                                "app-template",
                                "get",
                                "full-test",
                                "-V",
                                "3.0.0",
                                "-o",
                                "json",
                                "-f",
                                temp_path,
                                "--cluster",
                                "test-cluster",
                                "--org",
                                "test-org",
                                "--project",
                                "test-project",
                            ]
                        )

        assert not capture.err
        assert f"Template saved to {temp_path}" in capture.out
        assert capture.code == 0

        # Check file content
        with open(temp_path) as f:
            content = f.read()
            assert '"template_name": "full-test"' in content
            assert '"template_version": "3.0.0"' in content
            assert '"param1": "test"' in content
    finally:
        import os

        if os.path.exists(temp_path):
            os.unlink(temp_path)