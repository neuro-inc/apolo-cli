from typing import Any, List

import pytest

from apolo_sdk import AppTemplate

from apolo_cli.formatters.app_templates import (
    AppTemplatesFormatter,
    SimpleAppTemplatesFormatter,
)


class TestAppTemplatesFormatter:
    @pytest.fixture
    def templates(self) -> List[AppTemplate]:
        return [
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

    def test_app_templates_formatter(
        self, templates: List[AppTemplate], rich_cmp: Any
    ) -> None:
        formatter = AppTemplatesFormatter()
        rich_cmp(formatter(templates))

    def test_simple_app_templates_formatter(
        self, templates: List[AppTemplate], rich_cmp: Any
    ) -> None:
        formatter = SimpleAppTemplatesFormatter()
        rich_cmp(formatter(templates))

    def test_app_templates_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = AppTemplatesFormatter()
        rich_cmp(formatter([]))

    def test_simple_app_templates_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = SimpleAppTemplatesFormatter()
        rich_cmp(formatter([]))
