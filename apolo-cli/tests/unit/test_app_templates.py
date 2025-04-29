from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Iterator, List
from unittest import mock

from apolo_sdk import AppTemplate
from apolo_sdk._apps import Apps

_RunCli = Any


@contextmanager
def mock_apps_list_template_versions(
    template_name: str, versions: List[str]
) -> Iterator[None]:
    """Context manager to mock the Apps.list_template_versions method."""
    with mock.patch.object(Apps, "list_template_versions") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs: Any) -> AsyncIterator[AsyncIterator[AppTemplate]]:
            async def async_iterator() -> AsyncIterator[AppTemplate]:
                for version in versions:
                    yield AppTemplate(
                        name=template_name,
                        version=version,
                        title=f"{template_name} {version}",
                        short_description=f"Version {version} of {template_name}",
                        tags=[],
                    )

            yield async_iterator()

        mocked.side_effect = async_cm
        yield


@contextmanager
def mock_apps_list_templates(templates: List[AppTemplate]) -> Iterator[None]:
    """Context manager to mock the Apps.list_templates method."""
    with mock.patch.object(Apps, "list_templates") as mocked:

        @asynccontextmanager
        async def async_cm(**kwargs: Any) -> AsyncIterator[AsyncIterator[AppTemplate]]:
            async def async_iterator() -> AsyncIterator[AppTemplate]:
                for template in templates:
                    yield template

            yield async_iterator()

        mocked.side_effect = async_cm
        yield


def test_app_template_ls_with_templates(run_cli: _RunCli) -> None:
    """Test the app_template ls command when templates are returned."""
    templates = [
        AppTemplate(
            name="stable-diffusion",
            title="Stable Diffusion",
            version="master",
            short_description="AI image generation model",
            tags=["ai", "image", "generation"],
        ),
        AppTemplate(
            name="jupyter-notebook",
            title="Jupyter Notebook",
            version="1.0.0",
            short_description="Interactive computing environment",
            tags=["jupyter", "notebook", "python"],
        ),
    ]

    with mock_apps_list_templates(templates):
        capture = run_cli(["app-template", "ls"])

    assert not capture.err
    assert "stable-diffusion" in capture.out
    assert "Stable Diffusion" in capture.out
    assert "master" in capture.out
    assert "AI image generation model" in capture.out
    assert "ai, image, generation" in capture.out
    assert capture.code == 0


def test_app_template_ls_no_templates(run_cli: _RunCli) -> None:
    """Test the app_template ls command when no templates are returned."""
    with mock_apps_list_templates([]):
        capture = run_cli(["app-template", "ls"])

    assert not capture.err
    assert "No app templates found." in capture.out
    assert capture.code == 0


def test_app_template_ls_quiet_mode(run_cli: _RunCli) -> None:
    """Test the app_template ls command in quiet mode."""
    templates = [
        AppTemplate(
            name="stable-diffusion",
            title="Stable Diffusion",
            version="master",
            short_description="AI image generation model",
            tags=["ai", "image", "generation"],
        ),
        AppTemplate(
            name="jupyter-notebook",
            title="Jupyter Notebook",
            version="1.0.0",
            short_description="Interactive computing environment",
            tags=["jupyter", "notebook", "python"],
        ),
    ]

    with mock_apps_list_templates(templates):
        capture = run_cli(["-q", "app-template", "ls"])

    assert not capture.err
    assert "stable-diffusion" in capture.out
    assert "jupyter-notebook" in capture.out
    assert "Stable Diffusion" not in capture.out  # Title should not be present
    assert capture.code == 0


def test_app_template_ls_quiet_mode_no_templates(run_cli: _RunCli) -> None:
    """Test the app_template ls command in quiet mode when no templates are returned."""
    with mock_apps_list_templates([]):
        capture = run_cli(["-q", "app-template", "ls"])

    assert not capture.err
    assert capture.out.strip() == ""
    assert capture.code == 0


def test_app_template_ls_versions_with_versions(run_cli: _RunCli) -> None:
    """Test the app_template ls-versions command when versions are returned."""
    versions = ["1.0.0", "1.1.0", "2.0.0"]

    with mock_apps_list_template_versions("stable-diffusion", versions):
        capture = run_cli(["app-template", "ls-versions", "stable-diffusion"])

    assert not capture.err
    assert "1.0.0" in capture.out
    assert "1.1.0" in capture.out
    assert "2.0.0" in capture.out
    assert "stable-diffusion" in capture.out
    assert capture.code == 0


def test_app_template_ls_versions_no_versions(run_cli: _RunCli) -> None:
    """Test the app_template ls-versions command when no versions are returned."""
    with mock_apps_list_template_versions("stable-diffusion", []):
        capture = run_cli(["app-template", "ls-versions", "stable-diffusion"])

    assert not capture.err
    assert "No versions found for app template 'stable-diffusion'" in capture.out
    assert capture.code == 0


def test_app_template_ls_versions_quiet_mode(run_cli: _RunCli) -> None:
    """Test the app_template ls-versions command in quiet mode."""
    versions = ["1.0.0", "2.0.0", "latest"]

    with mock_apps_list_template_versions("stable-diffusion", versions):
        capture = run_cli(["-q", "app-template", "ls-versions", "stable-diffusion"])

    assert not capture.err
    # In quiet mode with is_version_list=True, we should expect only version numbers
    assert (
        "stable-diffusion" not in capture.out
    )  # Template name should not be in output
    assert "1.0.0" in capture.out
    assert "2.0.0" in capture.out
    assert "latest" in capture.out
    assert capture.code == 0


def test_app_template_ls_versions_quiet_mode_no_versions(run_cli: _RunCli) -> None:
    with mock_apps_list_template_versions("stable-diffusion", []):
        capture = run_cli(["-q", "app-template", "ls-versions", "stable-diffusion"])

    assert not capture.err
    assert capture.out.strip() == ""
    assert capture.code == 0


def test_app_template_ls_versions_with_cluster_option(run_cli: _RunCli) -> None:
    """Test the app_template ls-versions command with cluster option."""
    versions = ["1.0.0"]

    # Need to patch the cluster validation first
    with mock.patch("apolo_cli.click_types.CLUSTER.convert") as convert_mock:
        convert_mock.return_value = "test-cluster"

        with mock_apps_list_template_versions("stable-diffusion", versions):
            capture = run_cli(
                [
                    "app-template",
                    "ls-versions",
                    "stable-diffusion",
                    "--cluster",
                    "test-cluster",
                ]
            )

    assert not capture.err
    assert "1.0.0" in capture.out
    assert capture.code == 0
