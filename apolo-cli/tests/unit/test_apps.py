from typing import AsyncIterator
from unittest import mock

import pytest

from apolo_sdk import AppInstance
from apolo_cli.apps import list as app_list


class TestAppList:
    @pytest.fixture
    def app_instances(self):
        return [
            AppInstance(
                id="704285b2-aab1-4b0a-b8ff-bfbeb37f89e4",
                name="superorg-test3-stable-diffusion-704285b2",
                display_name="Stable Diffusion",
                template_name="stable-diffusion",
                template_version="master",
                project_name="test3",
                org_name="superorg",
                state="errored",
            ),
            AppInstance(
                id="a4723404-f5e2-48b5-b709-629754b5056f",
                name="superorg-test3-stable-diffusion-a4723404",
                display_name="Stable Diffusion",
                template_name="stable-diffusion",
                template_version="master",
                project_name="test3",
                org_name="superorg",
                state="errored",
            ),
        ]

    async def test_app_list(self, app_instances, root, capsys):
        # Mock the client.apps.list method
        async def list_mock(*args, **kwargs):
            for instance in app_instances:
                yield instance

        root.client.apps.list = mock.AsyncMock(side_effect=list_mock)

        # Call the list command
        await app_list(root, "default", "superorg", "test3")

        # Check the output
        captured = capsys.readouterr()
        assert "704285b2-aab1-4b0a-b8ff-bfbeb37f89e4" in captured.out
        assert "superorg-test3-stable-diffusion-704285b2" in captured.out
        assert "Stable Diffusion" in captured.out
        assert "stable-diffusion" in captured.out
        assert "master" in captured.out
        assert "errored" in captured.out

    async def test_app_list_empty(self, root, capsys):
        # Mock the client.apps.list method to return no instances
        async def empty_list_mock(*args, **kwargs):
            return
            yield  # This makes it an async generator

        root.client.apps.list = mock.AsyncMock(side_effect=empty_list_mock)

        # Call the list command
        await app_list(root, "default", "superorg", "test3")

        # Check the output
        captured = capsys.readouterr()
        assert "No app instances found." in captured.out
