import asyncio
import enum
import json
import logging
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from functools import partial
from typing import (
    Any,
    AsyncIterator,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Set,
    overload,
)

import aiohttp
import aiohttp.hdrs
import attr
from aiodocker.exceptions import DockerError
from aiohttp import WSMsgType, WSServerHandshakeError
from dateutil.parser import isoparse
from multidict import MultiDict
from yarl import URL

from ._abc import (
    AbstractDockerImageProgress,
    ImageCommitFinished,
    ImageCommitStarted,
    ImageProgressPush,
    ImageProgressSave,
)
from ._config import Config
from ._core import _Core
from ._errors import NDJSONError, StdStreamError
from ._images import (
    _DummyProgress,
    _raise_on_error_chunk,
    _try_parse_image_progress_step,
)
from ._parser import DiskVolume, Parser, SecretFile, Volume
from ._parsing_utils import LocalImage, RemoteImage
from ._rewrite import rewrite_module
from ._url_utils import (
    normalize_disk_uri,
    normalize_secret_uri,
    normalize_storage_path_uri,
)
from ._utils import NoPublicConstructor, asyncgeneratorcontextmanager

log = logging.getLogger(__package__)

INVALID_IMAGE_NAME = "INVALID-IMAGE-NAME"


@rewrite_module
@dataclass(frozen=True)
class Resources:
    memory: int
    cpu: float
    nvidia_gpu: Optional[int] = None
    amd_gpu: Optional[int] = None
    intel_gpu: Optional[int] = None
    nvidia_gpu_model: Optional[str] = None
    amd_gpu_model: Optional[str] = None
    intel_gpu_model: Optional[str] = None
    shm: bool = True
    tpu_type: Optional[str] = None
    tpu_software_version: Optional[str] = None

    @property
    def memory_mb(self) -> int:
        return self.memory // 2**20


@rewrite_module
class JobStatus(str, enum.Enum):
    """An Enum subclass that represents job statuses.

    PENDING: a job is being created and scheduled. This includes finding (and
    possibly waiting for) sufficient amount of resources, pulling an image
    from a registry etc.
    SUSPENDED: a preemptible job is paused to allow other jobs to run.
    RUNNING: a job is being run.
    SUCCEEDED: a job terminated with the 0 exit code.
    CANCELLED: a running job was manually terminated/deleted.
    FAILED: a job terminated with a non-0 exit code.
    """

    PENDING = "pending"
    SUSPENDED = "suspended"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"  # invalid status code, a default value is status is not sent

    @property
    def is_pending(self) -> bool:
        cls = type(self)
        return self in (cls.PENDING, cls.SUSPENDED)

    @property
    def is_running(self) -> bool:
        return self == type(self).RUNNING

    @property
    def is_finished(self) -> bool:
        cls = type(self)
        return self in (cls.SUCCEEDED, cls.FAILED, cls.CANCELLED)

    @classmethod
    def items(cls) -> Set["JobStatus"]:
        return {item for item in cls if item != cls.UNKNOWN}

    @classmethod
    def active_items(cls) -> Set["JobStatus"]:
        return {item for item in cls.items() if not item.is_finished}

    @classmethod
    def finished_items(cls) -> Set["JobStatus"]:
        return {item for item in cls.items() if item.is_finished}

    __format__ = str.__format__  # type: ignore[assignment]
    __str__ = str.__str__


@rewrite_module
@dataclass(frozen=True)
class HTTPPort:
    port: int
    requires_auth: bool = True


@rewrite_module
@dataclass(frozen=True)
class Container:
    image: RemoteImage
    resources: Resources
    entrypoint: Optional[str] = None
    command: Optional[str] = None
    working_dir: Optional[str] = None
    http: Optional[HTTPPort] = None
    env: Mapping[str, str] = field(default_factory=dict)
    volumes: Sequence[Volume] = field(default_factory=list)
    secret_env: Mapping[str, URL] = field(default_factory=dict)
    secret_files: Sequence[SecretFile] = field(default_factory=list)
    disk_volumes: Sequence[DiskVolume] = field(default_factory=list)
    tty: bool = False


@rewrite_module
@dataclass(frozen=True)
class JobStatusItem:
    status: JobStatus
    transition_time: datetime
    reason: str = ""
    description: str = ""
    exit_code: Optional[int] = None


@rewrite_module
@dataclass(frozen=True)
class JobStatusHistory:
    status: JobStatus
    reason: str
    description: str
    restarts: int = 0
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    run_time_seconds: Optional[int] = None
    exit_code: Optional[int] = None
    transitions: Sequence[JobStatusItem] = field(default_factory=list)

    @property
    def changed_at(self) -> datetime:
        if self.status == JobStatus.PENDING:
            when = self.created_at
        elif self.status == JobStatus.RUNNING:
            when = self.started_at
        elif self.status == JobStatus.RUNNING or self.status == JobStatus.SUSPENDED:
            when = self.started_at
        elif self.status.is_finished:
            when = self.finished_at
        else:
            when = self.transitions[-1].transition_time
        assert when is not None
        return when


@rewrite_module
class JobRestartPolicy(str, enum.Enum):
    NEVER = "never"
    ON_FAILURE = "on-failure"
    ALWAYS = "always"

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return repr(self.value)


@rewrite_module
class JobPriority(enum.IntEnum):
    LOW = enum.auto()
    NORMAL = enum.auto()
    HIGH = enum.auto()


@rewrite_module
@dataclass(frozen=True)
class JobDescriptionInternal:
    materialized: bool = False
    being_dropped: bool = False
    logs_removed: bool = False


@rewrite_module
@dataclass(frozen=True)
class JobDescription:
    id: str
    owner: str
    cluster_name: str
    org_name: Optional[str]
    project_name: str
    namespace: str
    status: JobStatus
    history: JobStatusHistory
    container: Container
    scheduler_enabled: bool
    pass_config: bool
    uri: URL
    total_price_credits: Decimal
    price_credits_per_hour: Decimal
    name: Optional[str] = None
    tags: Sequence[str] = ()
    description: Optional[str] = None
    http_url: URL = URL()
    internal_hostname: Optional[str] = None
    internal_hostname_named: Optional[str] = None
    restart_policy: JobRestartPolicy = JobRestartPolicy.NEVER
    life_span: Optional[float] = None
    schedule_timeout: Optional[float] = None
    preset_name: Optional[str] = None
    preemptible_node: bool = False
    privileged: bool = False
    priority: JobPriority = JobPriority.NORMAL
    energy_schedule_name: Optional[str] = None
    _internal: JobDescriptionInternal = JobDescriptionInternal()


@rewrite_module
@dataclass(frozen=True)
class JobTelemetry:
    cpu: float
    memory_bytes: int
    timestamp: float
    gpu_duty_cycle: Optional[int] = None
    gpu_memory_bytes: Optional[int] = None

    @property
    def memory(self) -> float:
        return self.memory_bytes / 2**20

    @property
    def gpu_memory(self) -> Optional[float]:
        if self.gpu_memory_bytes is None:
            return None
        return self.gpu_memory_bytes / 2**20


@rewrite_module
@dataclass(frozen=True)
class Message:
    fileno: int
    data: bytes


@rewrite_module
class StdStream:
    def __init__(self, ws: aiohttp.ClientWebSocketResponse) -> None:
        self._ws = ws
        self._closing = False

    async def close(self) -> None:
        self._closing = True
        await self._ws.close()

    async def read_out(self) -> Optional[Message]:
        if self._closing:
            return None
        msg = await self._ws.receive()
        if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSING, WSMsgType.CLOSED):
            self._closing = True
            return None
        if msg.type == aiohttp.WSMsgType.ERROR:
            raise self._ws.exception()  # type: ignore
        if msg.type != aiohttp.WSMsgType.BINARY:
            raise RuntimeError(f"Incorrecr WebSocket message: {msg!r}")
        if msg.data[0] == 3:
            try:
                details = json.loads(msg.data[1:])
                exit_code = details["exit_code"]
            except Exception:
                exit_code = 1
            self._closing = True
            raise StdStreamError(exit_code)
        return Message(msg.data[0], msg.data[1:])

    async def write_in(self, data: bytes) -> None:
        if self._closing:
            return
        await self._ws.send_bytes(b"\x00" + data)

    async def resize(self, h: int, w: int) -> None:
        if self._closing:
            return
        await self._ws.send_bytes(b"\x04" + f'{{"height":{h},"width":{w}}}'.encode())


@rewrite_module
class Jobs(metaclass=NoPublicConstructor):
    def __init__(self, core: _Core, config: Config, parse: Parser) -> None:
        self._core = core
        self._config = config
        self._parse = parse

    def _get_monitoring_url(self, cluster_name: Optional[str]) -> URL:
        if cluster_name is None:
            cluster_name = self._config.cluster_name
        return self._config.get_cluster(cluster_name).monitoring_url

    async def run(
        self,
        container: Container,
        *,
        name: Optional[str] = None,
        tags: Sequence[str] = (),
        description: Optional[str] = None,
        scheduler_enabled: bool = False,
        pass_config: bool = False,
        wait_for_jobs_quota: bool = False,
        schedule_timeout: Optional[float] = None,
        restart_policy: JobRestartPolicy = JobRestartPolicy.NEVER,
        life_span: Optional[float] = None,
        org_name: Optional[str] = None,
        priority: Optional[JobPriority] = None,
        project_name: Optional[str] = None,
    ) -> JobDescription:
        url = self._config.api_url / "jobs"
        if not project_name:
            project_name = self._config.project_name_or_raise
        payload = _job_to_api(
            cluster_name=self._config.cluster_name,
            project_name=project_name,
            name=name,
            tags=tags,
            description=description,
            pass_config=pass_config,
            wait_for_jobs_quota=wait_for_jobs_quota,
            schedule_timeout=schedule_timeout,
            restart_policy=restart_policy,
            life_span=life_span,
            org_name=org_name or self._config.org_name,
            priority=priority,
        )
        payload["container"] = _container_to_api(
            config=self._config,
            image=container.image,
            entrypoint=container.entrypoint,
            command=container.command,
            working_dir=container.working_dir,
            http=container.http,
            env=container.env,
            volumes=container.volumes,
            secret_env=container.secret_env,
            secret_files=container.secret_files,
            disk_volumes=container.disk_volumes,
            tty=container.tty,
        )
        payload["container"]["resources"] = _resources_to_api(container.resources)
        payload["scheduler_enabled"] = scheduler_enabled
        auth = await self._config._api_auth()
        async with self._core.request("POST", url, json=payload, auth=auth) as resp:
            res = await resp.json()
            return _job_description_from_api(res, self._parse)

    async def start(
        self,
        *,
        image: RemoteImage,
        preset_name: str,
        cluster_name: Optional[str] = None,
        org_name: Optional[str] = None,
        entrypoint: Optional[str] = None,
        command: Optional[str] = None,
        working_dir: Optional[str] = None,
        http: Optional[HTTPPort] = None,
        env: Optional[Mapping[str, str]] = None,
        volumes: Sequence[Volume] = (),
        secret_env: Optional[Mapping[str, URL]] = None,
        secret_files: Sequence[SecretFile] = (),
        disk_volumes: Sequence[DiskVolume] = (),
        tty: bool = False,
        shm: bool = False,
        name: Optional[str] = None,
        tags: Sequence[str] = (),
        description: Optional[str] = None,
        pass_config: bool = False,
        wait_for_jobs_quota: bool = False,
        schedule_timeout: Optional[float] = None,
        restart_policy: JobRestartPolicy = JobRestartPolicy.NEVER,
        life_span: Optional[float] = None,
        privileged: bool = False,
        priority: Optional[JobPriority] = None,
        energy_schedule_name: Optional[str] = None,
        project_name: Optional[str] = None,
    ) -> JobDescription:
        url = (self._config.api_url / "jobs").with_query("from_preset")
        container_payload = _container_to_api(
            config=self._config,
            image=image,
            entrypoint=entrypoint,
            command=command,
            working_dir=working_dir,
            http=http,
            env=env,
            volumes=volumes,
            secret_env=secret_env,
            secret_files=secret_files,
            disk_volumes=disk_volumes,
            tty=tty,
            shm=shm,
        )
        payload = _job_to_api(
            cluster_name=cluster_name or self._config.cluster_name,
            project_name=project_name or self._config.project_name_or_raise,
            name=name,
            preset_name=preset_name,
            tags=tags,
            description=description,
            pass_config=pass_config,
            wait_for_jobs_quota=wait_for_jobs_quota,
            schedule_timeout=schedule_timeout,
            restart_policy=restart_policy,
            life_span=life_span,
            privileged=privileged,
            org_name=org_name or self._config.org_name,
            priority=priority,
            energy_schedule_name=energy_schedule_name,
        )
        payload.update(**container_payload)
        auth = await self._config._api_auth()
        async with self._core.request("POST", url, json=payload, auth=auth) as resp:
            res = await resp.json()
            return _job_description_from_api(res, self._parse)

    @asyncgeneratorcontextmanager
    async def list(
        self,
        *,
        statuses: Iterable[JobStatus] = (),
        name: str = "",
        tags: Iterable[str] = (),
        owners: Iterable[str] = (),
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        reverse: bool = False,
        limit: Optional[int] = None,
        cluster_name: Optional[str] = None,
        org_names: Iterable[Optional[str]] = (),
        project_names: Iterable[str] = (),
        _materialized: Optional[bool] = None,
        _being_dropped: Optional[bool] = False,
        _logs_removed: Optional[bool] = False,
    ) -> AsyncIterator[JobDescription]:
        if not org_names:
            org_names = [self._config.org_name]
        url = self._config.api_url / "jobs"
        headers = {"Accept": "application/x-ndjson"}
        params: MultiDict[str] = MultiDict()
        for status in statuses:
            params.add("status", status.value)
        if name:
            params.add("name", name)
        for owner in owners:
            params.add("owner", owner)
        for tag in tags:
            params.add("tag", tag)
        if since:
            if since.tzinfo is None:
                # Interpret naive datetime object as local time.
                since = since.astimezone(timezone.utc)
            params.add("since", since.isoformat())
        if until:
            if until.tzinfo is None:
                until = until.astimezone(timezone.utc)
            params.add("until", until.isoformat())
        if cluster_name is None:
            cluster_name = self._config.cluster_name
        params["cluster_name"] = cluster_name
        if reverse:
            params.add("reverse", "1")
        if limit is not None:
            params.add("limit", str(limit))
        if _materialized is not None:
            params.add("materialized", str(_materialized))
        if _being_dropped is not None:
            params.add("being_dropped", str(_being_dropped))
        if _logs_removed is not None:
            params.add("logs_removed", str(_logs_removed))
        for org_name in org_names:
            if org_name is not None:
                params.add("org_name", org_name)
        for project_name in project_names:
            params.add("project_name", project_name)
        auth = await self._config._api_auth()
        async with self._core.request(
            "GET", url, headers=headers, params=params, auth=auth
        ) as resp:
            if resp.headers.get("Content-Type", "").startswith("application/x-ndjson"):
                async for line in resp.content:
                    server_message = json.loads(line)
                    if "error" in server_message:
                        raise NDJSONError(server_message["error"])
                    yield _job_description_from_api(server_message, self._parse)
            else:
                ret = await resp.json()
                for j in ret["jobs"]:
                    yield _job_description_from_api(j, self._parse)

    async def kill(self, id: str) -> None:
        url = self._config.api_url / "jobs" / id
        auth = await self._config._api_auth()
        async with self._core.request("DELETE", url, auth=auth):
            # an error is raised for status >= 400
            return None  # 201 status code

    async def bump_life_span(self, id: str, additional_life_span: float) -> None:
        url = self._config.api_url / "jobs" / id / "max_run_time_minutes"
        payload = {
            "additional_max_run_time_minutes": int(additional_life_span // 60),
        }
        auth = await self._config._api_auth()
        async with self._core.request("PUT", url, json=payload, auth=auth):
            # an error is raised for status >= 400
            return None  # 201 status code

    @asyncgeneratorcontextmanager
    async def monitor(
        self,
        id: str,
        *,
        cluster_name: Optional[str] = None,
        since: Optional[datetime] = None,
        timestamps: bool = False,
        separator: Optional[str] = None,
        debug: bool = False,
    ) -> AsyncIterator[bytes]:
        url = self._get_monitoring_url(cluster_name) / id / "log_ws"
        if since is not None:
            if since.tzinfo is None:
                # Interpret naive datetime object as local time.
                since = since.astimezone(timezone.utc)
            url = url.update_query(since=since.isoformat())
        if timestamps:
            url = url.update_query(timestamps="true")
        if separator is not None:
            url = url.update_query(separator=separator)
        if debug:
            url = url.update_query(debug="true")
        auth = await self._config._api_auth()
        async with self._core.ws_connect(
            url,
            auth=auth,
            timeout=None,
            heartbeat=30,
        ) as ws:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.BINARY:
                    if msg.data:
                        yield msg.data
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    raise ws.exception()  # type: ignore
                else:
                    raise RuntimeError(f"Incorrecr WebSocket message: {msg!r}")

    async def status(self, id: str) -> JobDescription:
        url = self._config.api_url / "jobs" / id
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            ret = await resp.json()
            return _job_description_from_api(ret, self._parse)

    @asyncgeneratorcontextmanager
    async def top(
        self, id: str, *, cluster_name: Optional[str] = None
    ) -> AsyncIterator[JobTelemetry]:
        url = self._get_monitoring_url(cluster_name) / id / "top"
        auth = await self._config._api_auth()
        try:
            received_any = False
            async with self._core.ws_connect(url, auth=auth) as ws:
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        yield _job_telemetry_from_api(msg.json())
                        received_any = True
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        raise ws.exception()  # type: ignore
                    else:
                        raise RuntimeError(f"Incorrecr WebSocket message: {msg!r}")
            if not received_any:
                raise ValueError(f"Job is not running. Job Id = {id}")
        except WSServerHandshakeError as e:
            if e.status == 400:
                raise ValueError(f"Job not found. Job Id = {id}")
            raise

    async def save(
        self,
        id: str,
        image: RemoteImage,
        *,
        progress: Optional[AbstractDockerImageProgress] = None,
        cluster_name: Optional[str] = None,
    ) -> None:
        if not image._is_in_apolo_registry:
            raise ValueError(f"Image `{image}` must be in the platform registry")
        if progress is None:
            progress = _DummyProgress()

        payload = {"container": {"image": image.as_docker_url()}}
        url = self._get_monitoring_url(cluster_name) / id / "save"

        auth = await self._config._api_auth()
        timeout = attr.evolve(self._core.timeout, sock_read=None)
        # `self._code.request` implicitly sets `total=3 * 60`
        # unless `sock_read is None`
        async with self._core.request(
            "POST", url, json=payload, timeout=timeout, auth=auth
        ) as resp:
            # first, we expect exactly two docker-commit messages
            progress.save(ImageProgressSave(id, image))

            chunk_1 = await resp.content.readline()
            data_1 = _parse_commit_started_chunk(id, _load_chunk(chunk_1), self._parse)
            progress.commit_started(data_1)

            chunk_2 = await resp.content.readline()
            data_2 = _parse_commit_finished_chunk(id, _load_chunk(chunk_2))
            progress.commit_finished(data_2)

            # then, we expect stream for docker-push
            src = LocalImage(f"{image.project_name}/{image.name}", image.tag)
            progress.push(ImageProgressPush(src, dst=image))
            async for chunk in resp.content:
                obj = _load_chunk(chunk)
                push_step = _try_parse_image_progress_step(obj, image.tag)
                if push_step:
                    progress.step(push_step)

    @asynccontextmanager
    async def port_forward(
        self,
        id: str,
        local_port: int,
        job_port: int,
        *,
        no_key_check: bool = False,
        cluster_name: Optional[str] = None,
    ) -> AsyncIterator[None]:
        srv = await asyncio.start_server(
            partial(
                self._port_forward, id=id, job_port=job_port, cluster_name=cluster_name
            ),
            "localhost",
            local_port,
        )
        try:
            yield
        finally:
            srv.close()
            await srv.wait_closed()

    async def _port_forward(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        id: str,
        job_port: int,
        *,
        cluster_name: Optional[str] = None,
    ) -> None:
        try:
            loop = asyncio.get_event_loop()
            url = self._get_monitoring_url(cluster_name)
            url = url / id / "port_forward" / str(job_port)
            async with self._core.ws_connect(
                url,
                auth=await self._config._api_auth(),
                timeout=None,
                receive_timeout=None,
                heartbeat=30,
            ) as ws:
                tasks = []
                tasks.append(loop.create_task(self._port_reader(ws, writer)))
                tasks.append(loop.create_task(self._port_writer(ws, reader)))
                try:
                    await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                finally:
                    for task in tasks:
                        if not task.done():
                            task.cancel()
                            with suppress(asyncio.CancelledError):
                                await task
                    writer.close()
                    await writer.wait_closed()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Unhandled exception during port-forwarding")
            writer.close()

    async def _port_reader(
        self, ws: aiohttp.ClientWebSocketResponse, writer: asyncio.StreamWriter
    ) -> None:
        async for msg in ws:
            if msg.type == aiohttp.WSMsgType.BINARY:
                writer.write(msg.data)
                await writer.drain()
            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise ws.exception()  # type: ignore
            else:
                raise RuntimeError(f"Incorrecr WebSocket message: {msg!r}")
        writer.close()
        await writer.wait_closed()

    async def _port_writer(
        self, ws: aiohttp.ClientWebSocketResponse, reader: asyncio.StreamReader
    ) -> None:
        while True:
            data = await reader.read(4 * 1024 * 1024)
            if not data:
                # EOF
                break
            await ws.send_bytes(data)

    @asynccontextmanager
    async def attach(
        self,
        id: str,
        *,
        tty: bool = False,
        stdin: bool = False,
        stdout: bool = False,
        stderr: bool = False,
        cluster_name: Optional[str] = None,
    ) -> AsyncIterator[StdStream]:
        url = self._get_monitoring_url(cluster_name) / id / "attach"
        url = url.with_query(
            tty=str(int(tty)),
            stdin=str(int(stdin)),
            stdout=str(int(stdout)),
            stderr=str(int(stderr)),
        )
        auth = await self._config._api_auth()

        async with self._core.ws_connect(
            url,
            auth=auth,
            headers={
                aiohttp.hdrs.SEC_WEBSOCKET_PROTOCOL: "v2.channels.neu.ro",
            },
            timeout=None,
            receive_timeout=None,
            heartbeat=30,
        ) as ws:
            yield StdStream(ws)

    @asynccontextmanager
    async def exec(
        self,
        id: str,
        cmd: str,
        *,
        tty: bool = False,
        stdin: bool = False,
        stdout: bool = False,
        stderr: bool = False,
        cluster_name: Optional[str] = None,
    ) -> AsyncIterator[StdStream]:
        url = self._get_monitoring_url(cluster_name) / id / "exec"
        url = url.with_query(
            cmd=cmd,
            tty=str(int(tty)),
            stdin=str(int(stdin)),
            stdout=str(int(stdout)),
            stderr=str(int(stderr)),
        )
        auth = await self._config._api_auth()

        async with self._core.ws_connect(
            url,
            auth=auth,
            timeout=None,
            receive_timeout=None,
            heartbeat=30,
        ) as ws:
            try:
                yield StdStream(ws)
            finally:
                await ws.close()

    async def send_signal(self, id: str, *, cluster_name: Optional[str] = None) -> None:
        url = self._get_monitoring_url(cluster_name) / id / "kill"
        auth = await self._config._api_auth()
        async with self._core.request("POST", url, auth=auth) as resp:
            resp

    async def get_capacity(
        self, *, cluster_name: Optional[str] = None
    ) -> Mapping[str, int]:
        url = self._get_monitoring_url(cluster_name) / "capacity"
        auth = await self._config._api_auth()
        async with self._core.request("GET", url, auth=auth) as resp:
            return await resp.json()


#  ############## Internal helpers ###################


def _load_chunk(chunk: bytes) -> Dict[str, Any]:
    return json.loads(chunk.decode())


def _parse_commit_started_chunk(
    job_id: str, obj: Dict[str, Any], parse: Parser
) -> ImageCommitStarted:
    _raise_for_invalid_commit_chunk(obj, expect_started=True)
    details_json = obj.get("details", {})
    image = details_json.get("image")
    if not image:
        raise DockerError(400, {"message": "Missing required details: 'image'"})
    return ImageCommitStarted(job_id, parse.remote_image(image))


def _parse_commit_finished_chunk(
    job_id: str, obj: Dict[str, Any]
) -> ImageCommitFinished:
    _raise_for_invalid_commit_chunk(obj, expect_started=False)
    return ImageCommitFinished(job_id)


def _raise_for_invalid_commit_chunk(obj: Dict[str, Any], expect_started: bool) -> None:
    _raise_on_error_chunk(obj)
    if "status" not in obj.keys():
        raise DockerError(400, {"message": 'Missing required field: "status"'})
    status = obj["status"]
    expected = "CommitStarted" if expect_started else "CommitFinished"
    if status != expected:
        raise DockerError(
            400,
            {"message": f"Invalid commit status: '{status}', expecting: '{expected}'"},
        )


def _resources_to_api(resources: Resources) -> Dict[str, Any]:
    value: Dict[str, Any] = {
        "memory": resources.memory,
        "cpu": resources.cpu,
        "shm": resources.shm,
    }
    if resources.nvidia_gpu:
        value["nvidia_gpu"] = resources.nvidia_gpu
    if resources.nvidia_gpu_model:
        value["nvidia_gpu_model"] = resources.nvidia_gpu_model
    if resources.amd_gpu:
        value["amd_gpu"] = resources.amd_gpu
    if resources.amd_gpu_model:
        value["amd_gpu_model"] = resources.amd_gpu_model
    if resources.intel_gpu:
        value["intel_gpu"] = resources.intel_gpu
    if resources.intel_gpu_model:
        value["intel_gpu_model"] = resources.intel_gpu_model
    if resources.tpu_type:
        assert resources.tpu_software_version
        value["tpu"] = {
            "type": resources.tpu_type,
            "software_version": resources.tpu_software_version,
        }
    return value


def _resources_from_api(data: Dict[str, Any]) -> Resources:
    tpu_type = tpu_software_version = None
    if "tpu" in data:
        tpu = data["tpu"]
        tpu_type = tpu["type"]
        tpu_software_version = tpu["software_version"]
    return Resources(
        memory=data["memory"],
        cpu=data["cpu"],
        shm=data.get("shm", True),
        nvidia_gpu=data.get("nvidia_gpu", None),
        amd_gpu=data.get("amd_gpu", None),
        intel_gpu=data.get("intel_gpu", None),
        nvidia_gpu_model=data.get("nvidia_gpu_model", None),
        amd_gpu_model=data.get("amd_gpu_model", None),
        intel_gpu_model=data.get("intel_gpu_model", None),
        tpu_type=tpu_type,
        tpu_software_version=tpu_software_version,
    )


def _http_port_to_api(port: HTTPPort) -> Dict[str, Any]:
    return {"port": port.port, "requires_auth": port.requires_auth}


def _http_port_from_api(data: Dict[str, Any]) -> HTTPPort:
    return HTTPPort(
        port=data.get("port", -1), requires_auth=data.get("requires_auth", False)
    )


def _container_from_api(
    data: Dict[str, Any],
    cluster_name: str,
    parse: Parser,
) -> Container:
    try:
        image = parse.remote_image(data["image"], cluster_name=cluster_name)
    except ValueError:
        image = RemoteImage.new_external_image(name=INVALID_IMAGE_NAME)

    return Container(
        image=image,
        resources=_resources_from_api(data["resources"]),
        entrypoint=data.get("entrypoint", None),
        command=data.get("command", None),
        working_dir=data.get("working_dir"),
        http=_http_port_from_api(data["http"]) if "http" in data else None,
        env=data.get("env", dict()),
        volumes=[_volume_from_api(v) for v in data.get("volumes", [])],
        secret_env={name: URL(val) for name, val in data.get("secret_env", {}).items()},
        secret_files=[_secret_file_from_api(v) for v in data.get("secret_volumes", [])],
        disk_volumes=[_disk_volume_from_api(v) for v in data.get("disk_volumes", [])],
        tty=data.get("tty", False),
    )


def _container_to_api(
    config: Config,
    image: RemoteImage,
    entrypoint: Optional[str] = None,
    command: Optional[str] = None,
    working_dir: Optional[str] = None,
    http: Optional[HTTPPort] = None,
    env: Optional[Mapping[str, str]] = None,
    volumes: Sequence[Volume] = (),
    secret_env: Optional[Mapping[str, URL]] = None,
    secret_files: Sequence[SecretFile] = (),
    disk_volumes: Sequence[DiskVolume] = (),
    tty: bool = False,
    shm: bool = False,
) -> Dict[str, Any]:
    primitive: Dict[str, Any] = {"image": image.as_docker_url()}
    if shm:
        primitive["resources"] = {"shm": shm}
    if entrypoint:
        primitive["entrypoint"] = entrypoint
    if command:
        primitive["command"] = command
    if working_dir:
        primitive["working_dir"] = working_dir
    if http:
        primitive["http"] = _http_port_to_api(http)
    if env:
        primitive["env"] = env
    if volumes:
        primitive["volumes"] = [_volume_to_api(v, config) for v in volumes]
    if secret_env:
        primitive["secret_env"] = {
            k: str(
                normalize_secret_uri(
                    v,
                    config.project_name_or_raise,
                    config.cluster_name,
                    config.org_name,
                )
            )
            for k, v in secret_env.items()
        }
    if secret_files:
        primitive["secret_volumes"] = [
            _secret_file_to_api(v, config) for v in secret_files
        ]
    if disk_volumes:
        primitive["disk_volumes"] = [
            _disk_volume_to_api(v, config) for v in disk_volumes
        ]
    if tty:
        primitive["tty"] = True
    return primitive


def _calc_status(stat: str) -> JobStatus:
    # Forward-compatible support for CANCELLED status
    try:
        return JobStatus(stat)
    except ValueError:
        return JobStatus.UNKNOWN


def _job_status_item_from_api(res: Dict[str, Any]) -> JobStatusItem:
    return JobStatusItem(
        status=_calc_status(res.get("status", "unknown")),
        transition_time=_parse_datetime(res["transition_time"]),
        reason=res.get("reason", ""),
        description=res.get("description", ""),
        exit_code=res.get("exit_code"),
    )


def _job_description_from_api(res: Dict[str, Any], parse: Parser) -> JobDescription:
    # TODO y.s.: maybe, catch KeyErrors and re-raise with an error message like
    #   "SDK and API has incompatible versions: {key} was not found in the API response"
    cluster_name = res["cluster_name"]
    container = _container_from_api(res["container"], cluster_name, parse)
    owner = res["owner"]
    name = res.get("name")
    tags = res.get("tags", ())
    description = res.get("description")
    history = JobStatusHistory(
        # Forward-compatible support for CANCELLED status
        status=_calc_status(res["history"].get("status", "unknown")),
        reason=res["history"].get("reason", ""),
        restarts=res["history"].get("restarts", 0),
        description=res["history"].get("description", ""),
        created_at=_parse_datetime(res["history"].get("created_at")),
        started_at=_parse_datetime(res["history"].get("started_at")),
        finished_at=_parse_datetime(res["history"].get("finished_at")),
        run_time_seconds=res["history"].get("run_time_seconds"),
        exit_code=res["history"].get("exit_code"),
        transitions=[
            _job_status_item_from_api(item_raw) for item_raw in res.get("statuses", [])
        ],
    )
    http_url = URL(res.get("http_url", ""))
    http_url_named = URL(res.get("http_url_named", ""))
    internal_hostname = res.get("internal_hostname", None)
    internal_hostname_named = res.get("internal_hostname_named", None)
    restart_policy = JobRestartPolicy(res.get("restart_policy", JobRestartPolicy.NEVER))
    max_run_time_minutes = res.get("max_run_time_minutes")
    life_span = (
        max_run_time_minutes * 60.0 if max_run_time_minutes is not None else None
    )
    # TODO: this change requires a new release of API with
    # https://github.com/neuro-inc/platform-api/pull/1770 merged
    total_price_credits = Decimal(res["total_price_credits"])
    price_credits_per_hour = Decimal(res["price_credits_per_hour"])
    priority = JobPriority[res.get("priority", JobPriority.NORMAL.name).upper()]
    return JobDescription(
        status=_calc_status(res["status"]),
        id=res["id"],
        owner=owner,
        cluster_name=cluster_name,
        org_name=res.get("org_name"),
        history=history,
        container=container,
        scheduler_enabled=res["scheduler_enabled"],
        preemptible_node=res.get("preemptible_node", False),
        pass_config=res["pass_config"],
        name=name,
        tags=tags,
        description=description,
        http_url=http_url_named or http_url,
        internal_hostname=internal_hostname,
        internal_hostname_named=internal_hostname_named,
        uri=URL(res["uri"]),
        restart_policy=restart_policy,
        life_span=life_span,
        schedule_timeout=res.get("schedule_timeout", None),
        preset_name=res.get("preset_name"),
        total_price_credits=total_price_credits,
        price_credits_per_hour=price_credits_per_hour,
        priority=priority,
        energy_schedule_name=res.get("energy_schedule_name"),
        project_name=res.get("project_name", owner),
        namespace=res.get("namespace", "") or "",
        _internal=JobDescriptionInternal(
            materialized=res.get("materialized", False),
            being_dropped=res.get("being_dropped", False),
            logs_removed=res.get("logs_removed", False),
        ),
    )


def _job_to_api(
    cluster_name: str,
    project_name: str,
    name: Optional[str] = None,
    preset_name: Optional[str] = None,
    tags: Sequence[str] = (),
    description: Optional[str] = None,
    pass_config: bool = False,
    wait_for_jobs_quota: bool = False,
    schedule_timeout: Optional[float] = None,
    restart_policy: JobRestartPolicy = JobRestartPolicy.NEVER,
    life_span: Optional[float] = None,
    privileged: bool = False,
    org_name: Optional[str] = None,
    priority: Optional[JobPriority] = None,
    energy_schedule_name: Optional[str] = None,
) -> Dict[str, Any]:
    primitive: Dict[str, Any] = {
        "pass_config": pass_config,
        "project_name": project_name,
    }
    if name:
        primitive["name"] = name
    if preset_name:
        primitive["preset_name"] = preset_name
    if tags:
        primitive["tags"] = tags
    if description:
        primitive["description"] = description
    if schedule_timeout:
        primitive["schedule_timeout"] = schedule_timeout
    if restart_policy != JobRestartPolicy.NEVER:
        primitive["restart_policy"] = str(restart_policy)
    if life_span is not None:
        primitive["max_run_time_minutes"] = int(life_span // 60)
    if wait_for_jobs_quota:
        primitive["wait_for_jobs_quota"] = wait_for_jobs_quota
    if privileged:
        primitive["privileged"] = privileged
    if org_name:
        primitive["org_name"] = org_name
    if priority:
        primitive["priority"] = priority.name.lower()
    if energy_schedule_name:
        primitive["energy_schedule_name"] = energy_schedule_name
    primitive["cluster_name"] = cluster_name
    return primitive


def _job_telemetry_from_api(value: Dict[str, Any]) -> JobTelemetry:
    return JobTelemetry(
        cpu=value["cpu"],
        memory_bytes=value["memory_bytes"],
        timestamp=value["timestamp"],
        gpu_duty_cycle=value.get("gpu_duty_cycle"),
        gpu_memory_bytes=value.get("gpu_memory_bytes"),
    )


def _volume_to_api(volume: Volume, config: Config) -> Dict[str, Any]:
    uri = normalize_storage_path_uri(
        volume.storage_uri,
        config.project_name_or_raise,
        config.cluster_name,
        config.org_name,
    )
    resp: Dict[str, Any] = {
        "src_storage_uri": str(uri),
        "dst_path": volume.container_path,
        "read_only": bool(volume.read_only),
    }
    return resp


def _secret_file_to_api(secret_file: SecretFile, config: Config) -> Dict[str, Any]:
    uri = normalize_secret_uri(
        secret_file.secret_uri,
        config.project_name_or_raise,
        config.cluster_name,
        config.org_name,
    )
    return {
        "src_secret_uri": str(uri),
        "dst_path": secret_file.container_path,
    }


def _disk_volume_to_api(volume: DiskVolume, config: Config) -> Dict[str, Any]:
    uri = normalize_disk_uri(
        volume.disk_uri,
        config.project_name_or_raise,
        config.cluster_name,
        config.org_name,
    )
    resp: Dict[str, Any] = {
        "src_disk_uri": str(uri),
        "dst_path": volume.container_path,
        "read_only": bool(volume.read_only),
    }
    return resp


def _volume_from_api(data: Dict[str, Any]) -> Volume:
    storage_uri = URL(data["src_storage_uri"])
    container_path = data["dst_path"]
    read_only = data.get("read_only", True)
    return Volume(
        storage_uri=storage_uri, container_path=container_path, read_only=read_only
    )


def _secret_file_from_api(data: Dict[str, Any]) -> SecretFile:
    secret_uri = URL(data["src_secret_uri"])
    container_path = data["dst_path"]
    return SecretFile(secret_uri, container_path)


def _disk_volume_from_api(data: Dict[str, Any]) -> DiskVolume:
    disk_uri = URL(data["src_disk_uri"])
    container_path = data["dst_path"]
    read_only = data.get("read_only", True)
    return DiskVolume(disk_uri, container_path, read_only)


@overload
def _parse_datetime(dt: str) -> datetime: ...


@overload
def _parse_datetime(dt: Optional[str]) -> Optional[datetime]: ...


def _parse_datetime(dt: Optional[str]) -> Optional[datetime]:
    if dt is None:
        return None
    return isoparse(dt)
