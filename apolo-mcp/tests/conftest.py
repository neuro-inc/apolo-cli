from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture()
def mock_client():
    """Provide a mock apolo_sdk.Client for unit tests.

    Usage:
        async def test_something(mock_client):
            mock_client.jobs.status.return_value = MagicMock(...)
            ...
    """
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    with patch("apolo_mcp._client.apolo_sdk.get", return_value=client):
        yield client
