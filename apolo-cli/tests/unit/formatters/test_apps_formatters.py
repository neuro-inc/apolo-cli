from datetime import datetime
from typing import Any

import pytest

from apolo_sdk import App, AppConfigurationRevision, AppEvent, AppEventResource

from apolo_cli.formatters.apps import (
    AppEventsFormatter,
    AppRevisionsFormatter,
    AppsFormatter,
    SimpleAppEventsFormatter,
    SimpleAppRevisionsFormatter,
    SimpleAppsFormatter,
)

from ..factories import _app_factory


class TestAppsFormatter:
    @pytest.fixture
    def apps(self) -> list[App]:
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

    def test_apps_formatter(self, apps: list[App], rich_cmp: Any) -> None:
        formatter = AppsFormatter()
        rich_cmp(formatter(apps))

    def test_simple_apps_formatter(self, apps: list[App], rich_cmp: Any) -> None:
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
    def events(self) -> list[AppEvent]:
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

    def test_app_events_formatter(self, events: list[AppEvent], rich_cmp: Any) -> None:
        formatter = AppEventsFormatter()
        rich_cmp(formatter(events))

    def test_simple_app_events_formatter(
        self, events: list[AppEvent], rich_cmp: Any
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


class TestAppRevisionsFormatter:
    @pytest.fixture
    def revisions(self) -> list[AppConfigurationRevision]:
        return [
            AppConfigurationRevision(
                revision_number=1,
                creator="admin-user",
                comment="Initial configuration",
                created_at=datetime.fromisoformat("2025-11-27T12:00:00+00:00"),
                end_at=datetime.fromisoformat("2025-11-27T13:00:00+00:00"),
            ),
            AppConfigurationRevision(
                revision_number=2,
                creator="test-user",
                comment="Update one",
                created_at=datetime.fromisoformat("2025-11-27T13:00:00+00:00"),
                end_at=datetime.fromisoformat("2025-11-27T14:00:00+00:00"),
            ),
            AppConfigurationRevision(
                revision_number=3,
                creator="test-user",
                comment="Some new changes",
                created_at=datetime.fromisoformat("2025-11-27T14:00:00+00:00"),
                end_at=None,
            ),
        ]

    def test_app_revisions_formatter(
        self, revisions: list[AppConfigurationRevision], rich_cmp: Any
    ) -> None:
        formatter = AppRevisionsFormatter()
        rich_cmp(formatter(revisions))

    def test_simple_app_revisions_formatter(
        self, revisions: list[AppConfigurationRevision], rich_cmp: Any
    ) -> None:
        formatter = SimpleAppRevisionsFormatter()
        rich_cmp(formatter(revisions))

    def test_app_revisions_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = AppRevisionsFormatter()
        rich_cmp(formatter([]))

    def test_simple_app_revisions_formatter_empty(self, rich_cmp: Any) -> None:
        formatter = SimpleAppRevisionsFormatter()
        rich_cmp(formatter([]))

    def test_app_revisions_formatter_with_none_comment(self, rich_cmp: Any) -> None:
        """Test that None comments are displayed as empty string."""
        revisions = [
            AppConfigurationRevision(
                revision_number=1,
                creator="test-user",
                comment=None,
                created_at=datetime.fromisoformat("2025-11-27T12:00:00+00:00"),
                end_at=datetime.fromisoformat("2025-11-27T13:00:00+00:00"),
            ),
        ]
        formatter = AppRevisionsFormatter()
        rich_cmp(formatter(revisions))
