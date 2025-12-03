from datetime import datetime
from typing import Any, List

import pytest

from apolo_sdk import App, AppEvent, AppEventResource

from apolo_cli.formatters.apps import (
    AppEventsFormatter,
    AppsFormatter,
    SimpleAppEventsFormatter,
    SimpleAppsFormatter,
)

from ..factories import _app_factory


class TestAppsFormatter:
    @pytest.fixture
    def apps(self) -> List[App]:
        return [
            _app_factory(
                id="704285b2-aab1-4b0a-b8ff-bfbeb37f89e4",
                name="superorg-test3-stable-diffusion-704285b2",
                display_name="Stable Diffusion",
                template_name="stable-diffusion",
                template_version="master",
                project_name="test3",
                org_name="superorg",
                state="errored",
            ),
            _app_factory(
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


class TestAppEventsFormatter:
    @pytest.fixture
    def events(self) -> List[AppEvent]:
        return [
            AppEvent(
                created_at=datetime.fromisoformat("2025-11-27T12:23:47.555539"),
                state="healthy",
                reason="Autoupdated",
                message=None,
                resources=[
                    AppEventResource(
                        kind="Deployment",
                        name="apolo-test-deployment",
                        uid="abc-123",
                        health_status="Healthy",
                        health_message=None,
                    ),
                    AppEventResource(
                        kind="Service",
                        name="apolo-test-service",
                        uid="def-456",
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

    def test_app_events_formatter(self, events: List[AppEvent], rich_cmp: Any) -> None:
        formatter = AppEventsFormatter()
        rich_cmp(formatter(events))

    def test_simple_app_events_formatter(
        self, events: List[AppEvent], rich_cmp: Any
    ) -> None:
        formatter = SimpleAppEventsFormatter()
        rich_cmp(formatter(events))

    def test_app_events_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = AppEventsFormatter()
        rich_cmp(formatter([]))

    def test_simple_app_events_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = SimpleAppEventsFormatter()
        rich_cmp(formatter([]))

    def test_app_events_formatter_with_message(self, rich_cmp: Any) -> None:
        events = [
            AppEvent(
                created_at=datetime.fromisoformat("2025-11-27T12:23:47.555539"),
                state="degraded",
                reason="DeploymentFailed",
                message="Deployment exceeded its progress deadline",
                resources=[
                    AppEventResource(
                        kind="Deployment",
                        name="test-deployment",
                        uid="xyz-789",
                        health_status="Degraded",
                        health_message="Deployment exceeded deadline",
                    ),
                ],
            ),
        ]
        formatter = AppEventsFormatter()
        rich_cmp(formatter(events))
