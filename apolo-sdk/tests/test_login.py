from collections.abc import AsyncIterator
from unittest import mock
from urllib.parse import parse_qsl

import aiohttp
import pytest
from aiohttp import ClientSession
from aiohttp.test_utils import unused_port
from aiohttp.web import (
    Application,
    HTTPBadRequest,
    HTTPForbidden,
    HTTPFound,
    HTTPOk,
    HTTPUnauthorized,
    Request,
    Response,
    json_response,
)
from yarl import URL

from apolo_sdk import AuthError
from apolo_sdk._login import (
    AuthCode,
    AuthNegotiator,
    AuthTokenClient,
    HeadlessNegotiator,
    _AuthConfig,
    _AuthToken,
    create_app_server,
    create_app_server_once,
    create_auth_code_app,
)

from tests import _TestServerFactory


class TestAuthCode:
    async def test_wait_timed_out(self) -> None:
        code = AuthCode()
        with pytest.raises(AuthError, match="failed to get an authorization code"):
            await code.wait(timeout_s=0.0)

    async def test_wait_cancelled(self) -> None:
        code = AuthCode()
        code.cancel()
        with pytest.raises(AuthError, match="failed to get an authorization code"):
            await code.wait()

    async def test_wait_exception(self) -> None:
        code = AuthCode()
        code.set_exception(AuthError("testerror"))
        with pytest.raises(AuthError, match="testerror"):
            await code.wait()

    async def test_wait(self) -> None:
        code = AuthCode()
        code.set_value("testcode")
        value = await code.wait()
        assert value == "testcode"


class TestAuthToken:
    def test_is_not_expired(self) -> None:
        token = _AuthToken.create(
            token="test_token",
            expires_in=100,
            refresh_token="test_refresh_token",
            now=2000.0,
        )
        assert token.token == "test_token"
        assert token.expiration_time == 2075
        assert not token.is_expired(now=2000)
        assert token.refresh_token == "test_refresh_token"

    def test_is_expired(self) -> None:
        token = _AuthToken.create(
            token="test_token",
            expires_in=0,
            refresh_token="test_refresh_token",
            now=2000.0,
        )
        assert token.token == "test_token"
        assert token.expiration_time == 2000
        assert token.is_expired(now=2000)
        assert token.refresh_token == "test_refresh_token"


class TestAuthCodeApp:
    @pytest.fixture
    async def client(self) -> AsyncIterator[ClientSession]:
        async with ClientSession() as client:
            yield client

    async def assert_code_callback_success(
        self,
        code: AuthCode,
        client: ClientSession,
        url: URL,
        redirect_url: URL | None = None,
    ) -> None:
        async with client.get(
            url, params={"code": "testcode"}, allow_redirects=False
        ) as resp:
            if redirect_url:
                assert resp.status == HTTPFound.status_code
                assert resp.headers["Location"] == str(redirect_url)
            else:
                assert resp.status == HTTPOk.status_code
                text = await resp.text()
                assert text == "OK"

        assert await code.wait() == "testcode"

    async def test_create_app_server_once(self, client: ClientSession) -> None:
        code = AuthCode()
        app = create_auth_code_app(code)

        port = unused_port()
        async with create_app_server_once(app, host="127.0.0.1", port=port) as url:
            assert url == URL(f"http://127.0.0.1:{port}")
            await self.assert_code_callback_success(code, client, url)

    async def test_create_app_server_redirect(self, client: ClientSession) -> None:
        code = AuthCode()
        redirect_url = URL("http://redirect.url")
        app = create_auth_code_app(code, redirect_url=redirect_url)

        port = unused_port()
        async with create_app_server_once(app, host="127.0.0.1", port=port) as url:
            assert url == URL(f"http://127.0.0.1:{port}")
            await self.assert_code_callback_success(
                code, client, url, redirect_url=redirect_url
            )

    async def test_create_app_server_once_failure(self, client: ClientSession) -> None:
        code = AuthCode()
        app = create_auth_code_app(code)

        port = unused_port()
        async with create_app_server_once(app, host="127.0.0.1", port=port) as url:
            assert url == URL(f"http://127.0.0.1:{port}")

            async with client.get(url) as resp:
                assert resp.status == HTTPBadRequest.status_code
                text = await resp.text()
                assert text == "The 'code' query parameter is missing."

            with pytest.raises(AuthError, match="failed to get an authorization code"):
                await code.wait()

    async def test_error_unauthorized(self, client: ClientSession) -> None:
        code = AuthCode()
        app = create_auth_code_app(code)

        port = unused_port()
        async with create_app_server_once(app, host="127.0.0.1", port=port) as url:
            assert url == URL(f"http://127.0.0.1:{port}")

            async with client.get(
                url,
                params={
                    "error": "unauthorized",
                    "error_description": "Test Unauthorized",
                },
            ) as resp:
                assert resp.status == HTTPUnauthorized.status_code
                text = await resp.text()
                assert text == "Test Unauthorized"

            with pytest.raises(AuthError, match="Test Unauthorized"):
                await code.wait()

    async def test_error_access_denied(self, client: ClientSession) -> None:
        code = AuthCode()
        app = create_auth_code_app(code)

        port = unused_port()
        async with create_app_server_once(app, host="127.0.0.1", port=port) as url:
            assert url == URL(f"http://127.0.0.1:{port}")

            async with client.get(
                url,
                params={
                    "error": "access_denied",
                    "error_description": "Test Access Denied",
                },
            ) as resp:
                assert resp.status == HTTPForbidden.status_code
                text = await resp.text()
                assert text == "Test Access Denied"

            with pytest.raises(AuthError, match="Test Access Denied"):
                await code.wait()

    async def test_error_other(self, client: ClientSession) -> None:
        code = AuthCode()
        app = create_auth_code_app(code)

        port = unused_port()
        async with create_app_server_once(app, host="127.0.0.1", port=port) as url:
            assert url == URL(f"http://127.0.0.1:{port}")

            async with client.get(
                url, params={"error": "other", "error_description": "Test Other"}
            ) as resp:
                assert resp.status == HTTPBadRequest.status_code
                text = await resp.text()
                assert text == "Test Other"

            with pytest.raises(AuthError, match="Test Other"):
                await code.wait()

    async def test_create_app_server(self, client: ClientSession) -> None:
        code = AuthCode()
        app = create_auth_code_app(code)

        port = unused_port()
        async with create_app_server(app, host="127.0.0.1", ports=[port]) as url:
            assert url == URL(f"http://127.0.0.1:{port}")
            await self.assert_code_callback_success(code, client, url)

    async def test_create_app_server_no_ports(self) -> None:
        code = AuthCode()
        app = create_auth_code_app(code)

        port = unused_port()
        async with create_app_server_once(app, host="127.0.0.1", port=port):
            with pytest.raises(RuntimeError, match="No free ports."):
                async with create_app_server(app, ports=[port]):
                    pass

    async def test_create_app_server_port_conflict(self, client: ClientSession) -> None:
        code = AuthCode()
        app = create_auth_code_app(code)
        outer_port = unused_port()
        inner_port = unused_port()
        async with create_app_server(app, ports=[outer_port, inner_port]) as url:
            assert url == URL(f"http://127.0.0.1:{outer_port}")
            async with create_app_server(app, ports=[outer_port, inner_port]) as url:
                assert url == URL(f"http://127.0.0.1:{inner_port}")
                await self.assert_code_callback_success(code, client, url)


class _TestAuthHandler:
    def __init__(self, client_id: str) -> None:
        self._client_id = client_id

        self._code = "test_code"
        self._token = "test_access_token"
        self._token_refreshed = "test_access_token_refreshed"
        self._refresh_token = "test_refresh_token"
        self._token_expires_in = 1234

    async def handle_authorize(self, request: Request) -> Response:
        # TODO: assert query
        url = URL(request.query["redirect_uri"]).with_query(code=self._code)
        raise HTTPFound(url)

    async def handle_token(self, request: Request) -> Response:
        assert request.headers["accept"] == "application/json"
        assert request.headers["content-type"] == "application/x-www-form-urlencoded"
        payload = dict(parse_qsl(await request.text()))
        grant_type = payload["grant_type"]
        if grant_type == "authorization_code":
            assert payload == {
                "grant_type": "authorization_code",
                "code_verifier": mock.ANY,
                "code": self._code,
                "client_id": self._client_id,
                "redirect_uri": mock.ANY,
            }
            resp_payload = {
                "access_token": self._token,
                "expires_in": self._token_expires_in,
                "refresh_token": self._refresh_token,
            }
        else:
            assert payload == {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": self._client_id,
            }
            resp_payload = {
                "access_token": self._token_refreshed,
                "expires_in": self._token_expires_in,
            }
        return json_response(resp_payload)


@pytest.fixture
def auth_client_id() -> str:
    return "test_client_id"


@pytest.fixture
async def auth_server(
    auth_client_id: str, aiohttp_server: _TestServerFactory
) -> AsyncIterator[URL]:
    handler = _TestAuthHandler(client_id=auth_client_id)
    app = Application()
    app.router.add_get("/authorize", handler.handle_authorize)
    app.router.add_post("/oauth/token", handler.handle_token)
    server = await aiohttp_server(app)
    yield server.make_url("/")


@pytest.fixture
async def auth_config(
    auth_client_id: str, auth_server: URL
) -> AsyncIterator[_AuthConfig]:
    port = unused_port()
    yield _AuthConfig.create(
        auth_url=auth_server / "authorize",
        token_url=auth_server / "oauth/token",
        logout_url=auth_server / "v2/logout",
        client_id=auth_client_id,
        audience="https://platform.api.dev.apolo.us",
        headless_callback_url=URL("https://api.dev.apolo.us/oauth/show-code"),
        callback_urls=[URL(f"http://127.0.0.1:{port}")],
    )


class TestTokenClient:
    async def test_request(self, auth_client_id: str, auth_config: _AuthConfig) -> None:
        code = AuthCode()
        code.set_value("test_code")
        code.callback_url = auth_config.callback_urls[0]

        async with aiohttp.ClientSession() as session:
            async with AuthTokenClient(
                session, auth_config.token_url, client_id=auth_client_id
            ) as client:
                token = await client.request(code)
                assert token.token == "test_access_token"
                assert token.refresh_token == "test_refresh_token"
                assert not token.is_expired()

    async def test_refresh(self, auth_client_id: str, auth_config: _AuthConfig) -> None:
        token = _AuthToken.create(
            token="test_access_token",
            expires_in=1234,
            refresh_token="test_refresh_token",
        )

        async with aiohttp.ClientSession() as session:
            async with AuthTokenClient(
                session, auth_config.token_url, client_id=auth_client_id
            ) as client:
                new_token = await client.refresh(token)
                assert new_token.token == "test_access_token_refreshed"
                assert new_token.refresh_token == "test_refresh_token"
                assert not token.is_expired()

    async def test_forbidden(
        self, aiohttp_server: _TestServerFactory, auth_config: _AuthConfig
    ) -> None:
        code = AuthCode()
        code.callback_url = auth_config.callback_urls[0]
        code.set_value("testcode")

        client_id = "test_client_id"

        async def handle_token(request: Request) -> Response:
            raise HTTPForbidden()

        app = Application()
        app.router.add_post("/oauth/token", handle_token)

        server = await aiohttp_server(app)
        url = server.make_url("/oauth/token")

        async with aiohttp.ClientSession() as session:
            async with AuthTokenClient(session, url, client_id=client_id) as client:
                with pytest.raises(AuthError, match="failed to get an access token."):
                    await client.request(code)

                with pytest.raises(AuthError, match="failed to get an access token."):
                    token = _AuthToken.create(
                        token="test_token",
                        expires_in=1234,
                        refresh_token="test_refresh_token",
                    )
                    await client.refresh(token)


class TestAuthNegotiator:
    async def show_dummy_browser(self, url: URL) -> None:
        async with ClientSession() as client:
            await client.get(url, allow_redirects=True)

    async def test_get_code(self, auth_config: _AuthConfig) -> None:
        async with aiohttp.ClientSession() as session:
            negotiator = AuthNegotiator(
                session, config=auth_config, show_browser_cb=self.show_dummy_browser
            )
            code = await negotiator.get_code()
            assert await code.wait() == "test_code"
            assert code.callback_url == auth_config.callback_urls[0]

    async def test_get_token(self, auth_config: _AuthConfig) -> None:
        async with aiohttp.ClientSession() as session:
            negotiator = AuthNegotiator(
                session, config=auth_config, show_browser_cb=self.show_dummy_browser
            )
            token = await negotiator.get_token()
            assert token.token == "test_access_token"
            assert token.refresh_token == "test_refresh_token"


class TestHeadlessNegotiator:
    async def test_get_code(self, auth_config: _AuthConfig) -> None:
        async def get_auth_code_cb(url: URL) -> str:
            assert url.with_query(None) == auth_config.auth_url

            assert dict(url.query) == {
                "response_type": "code",
                "code_challenge": mock.ANY,
                "code_challenge_method": "S256",
                "client_id": "test_client_id",
                "redirect_uri": "https://api.dev.apolo.us/oauth/show-code",
                "scope": "offline_access",
                "audience": "https://platform.api.dev.apolo.us",
            }
            return "test_code"

        async with aiohttp.ClientSession() as session:
            negotiator = HeadlessNegotiator(
                session, config=auth_config, get_auth_code_cb=get_auth_code_cb
            )
            code = await negotiator.get_code()
            assert await code.wait() == "test_code"

    async def test_get_code_raises(self, auth_config: _AuthConfig) -> None:
        async def get_auth_code_cb(url: URL) -> str:
            raise RuntimeError("callback error")

        async with aiohttp.ClientSession() as session:
            negotiator = HeadlessNegotiator(
                session, config=auth_config, get_auth_code_cb=get_auth_code_cb
            )
            with pytest.raises(RuntimeError, match="callback error"):
                await negotiator.get_code()
