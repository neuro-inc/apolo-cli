from contextlib import asynccontextmanager, contextmanager
from typing import Any, AsyncIterator, Iterator, List
from unittest import mock

from apolo_sdk import AppTemplate
from apolo_sdk._apps import Apps

_RunCli = Any


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
