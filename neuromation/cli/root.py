import logging
import re
from dataclasses import dataclass
from http.cookies import Morsel  # noqa
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Optional, Tuple

import aiohttp
import click
from yarl import URL

from neuromation.api import Client, Factory, Preset, gen_trace_id
from neuromation.api.config import _Config
from neuromation.api.config_factory import ConfigError


log = logging.getLogger(__name__)


TEXT_TYPE = ("application/json", "text")

HEADER_TOKEN_PATTERNS = [
    re.compile(rf"({auth_scheme})\s+([^ ]+\.[^ ]+\.[^ ]+)")
    for auth_scheme in ("Bearer", "Basic")
]


@dataclass
class Root:
    color: bool
    tty: bool
    terminal_size: Tuple[int, int]
    disable_pypi_version_check: bool
    network_timeout: float
    config_path: Path
    trace: bool
    verbosity: int

    _client: Optional[Client] = None
    _factory: Optional[Factory] = None

    @property
    def _config(self) -> _Config:
        assert self._client is not None
        return self._client._config

    @property
    def quiet(self) -> bool:
        return self.verbosity < 0

    @property
    def auth(self) -> Optional[str]:
        if self._client is not None:
            return self._config.auth_token.token
        return None

    @property
    def timeout(self) -> aiohttp.ClientTimeout:
        return aiohttp.ClientTimeout(
            None, None, self.network_timeout, self.network_timeout
        )

    @property
    def username(self) -> str:
        if self._client is None:
            raise ConfigError("User is not registered, run 'neuro login'.")
        return self._config.auth_token.username

    @property
    def url(self) -> URL:
        if self._client is None:
            raise ConfigError("User is not registered, run 'neuro login'.")
        return self._config.url

    @property
    def registry_url(self) -> URL:
        if self._client is None or not self._config.cluster_config.is_initialized():
            raise ConfigError("User is not registered, run 'neuro login'.")
        return self._config.cluster_config.registry_url

    @property
    def resource_presets(self) -> Dict[str, Preset]:
        if self._client is None or not self._config.cluster_config.is_initialized():
            raise ConfigError("User is not registered, run 'neuro login'.")
        return self._config.cluster_config.resource_presets

    @property
    def client(self) -> Client:
        assert self._client is not None
        return self._client

    async def init_client(self) -> None:
        trace_configs: Optional[List[aiohttp.TraceConfig]]
        if self.trace:
            trace_configs = [self._create_trace_config()]
        else:
            trace_configs = None
        self._factory = Factory(
            path=self.config_path, trace_configs=trace_configs, trace_id=gen_trace_id()
        )
        client = await self._factory.get(timeout=self.timeout)

        self._client = client

    def _create_trace_config(self) -> aiohttp.TraceConfig:
        trace_config = aiohttp.TraceConfig()
        trace_config.on_request_start.append(self._on_request_start)  # type: ignore
        trace_config.on_request_chunk_sent.append(
            self._on_request_chunk_sent  # type: ignore
        )
        trace_config.on_request_end.append(self._on_request_end)  # type: ignore
        trace_config.on_response_chunk_received.append(
            self._on_response_chunk_received  # type: ignore
        )
        return trace_config

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

    def get_session_cookie(self) -> Optional["Morsel[str]"]:
        if self._client is None:
            return None
        return self._client._get_session_cookie()

    def _print_debug(self, lines: List[str]) -> None:
        txt = "\n".join(click.style(line, dim=True) for line in lines)
        click.echo(txt, err=True)

    def _process_chunk(self, chunk: bytes, printable: bool) -> List[str]:
        if not chunk:
            return []
        if printable:
            return chunk.decode(errors="replace").split("\n")
        else:
            return [f"[binary {len(chunk)} bytes]"]

    async def _on_request_start(
        self,
        session: aiohttp.ClientSession,
        context: SimpleNamespace,
        data: aiohttp.TraceRequestStartParams,
    ) -> None:
        path = data.url.raw_path
        if data.url.raw_query_string:
            path += "?" + data.url.raw_query_string
        lines = [f"> {data.method} {path} HTTP/1.1"]
        for key, val in data.headers.items():
            lines.append(f"> {key}: {self._sanitize_header_value(val)}")
        lines.append("> ")
        self._print_debug(lines)

        content_type = data.headers.get("Content-Type", "")
        context.request_printable = content_type.startswith(TEXT_TYPE)

    async def _on_request_chunk_sent(
        self,
        session: aiohttp.ClientSession,
        context: SimpleNamespace,
        data: aiohttp.TraceRequestChunkSentParams,
    ) -> None:
        chunk = data.chunk
        lines = [
            "> " + line
            for line in self._process_chunk(chunk, context.request_printable)
        ]
        self._print_debug(lines)

    async def _on_request_end(
        self,
        session: aiohttp.ClientSession,
        context: SimpleNamespace,
        data: aiohttp.TraceRequestEndParams,
    ) -> None:
        lines = [f"< HTTP/1.1 {data.response.status} {data.response.reason}"]
        for key, val in data.response.headers.items():
            lines.append(f"< {key}: {val}")
        self._print_debug(lines)

        content_type = data.response.headers.get("Content-Type", "")
        context.response_printable = content_type.startswith(TEXT_TYPE)

    async def _on_response_chunk_received(
        self,
        session: aiohttp.ClientSession,
        context: SimpleNamespace,
        data: aiohttp.TraceResponseChunkReceivedParams,
    ) -> None:
        chunk = data.chunk
        lines = [
            "< " + line
            for line in self._process_chunk(chunk, context.response_printable)
        ]
        self._print_debug(lines)

    def _sanitize_header_value(self, text: str) -> str:
        for pattern in HEADER_TOKEN_PATTERNS:
            text = pattern.sub(r"\1 <token>", text)
        return text
