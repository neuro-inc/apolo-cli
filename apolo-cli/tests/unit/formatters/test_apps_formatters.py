from typing import Any, List

import pytest

from apolo_sdk import App

from apolo_cli.formatters.apps import AppsFormatter, SimpleAppsFormatter


class TestAppsFormatter:
    @pytest.fixture
    def apps(self) -> List[App]:
        return [
            App(
                id="704285b2-aab1-4b0a-b8ff-bfbeb37f89e4",
                name="superorg-test3-stable-diffusion-704285b2",
                display_name="Stable Diffusion",
                template_name="stable-diffusion",
                template_version="master",
                project_name="test3",
                org_name="superorg",
                state="errored",
            ),
            App(
                id="a4723404-f5e2-48b5-b709-629754b5056f",
                name="superorg-test3-stable-diffusion-a4723404",
                display_name="Stable Diffusion",
                template_name="stable-diffusion",
                template_version="master",
                project_name="test3",
                org_name="superorg",
                state="running",
            ),
        ]

    def test_apps_formatter(self, apps: List[App], rich_cmp: Any) -> None:
        formatter = AppsFormatter()
        rich_cmp(formatter(apps))

    def test_simple_apps_formatter(self, apps: List[App], rich_cmp: Any) -> None:
        formatter = SimpleAppsFormatter()
        rich_cmp(formatter(apps))

    def test_apps_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = AppsFormatter()
        rich_cmp(formatter([]))

    def test_simple_apps_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = SimpleAppsFormatter()
        rich_cmp(formatter([]))
