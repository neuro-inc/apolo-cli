import asyncio
import contextlib
import dataclasses
import logging
import shlex
import sys
import webbrowser
from collections.abc import AsyncIterator, Sequence
from contextlib import AsyncExitStack
from datetime import datetime, timedelta, timezone

import click
from dateutil.parser import isoparse
from yarl import URL

if sys.version_info >= (3, 11):
    import asyncio as async_timeout
else:
    import async_timeout

from apolo_sdk import (
    PASS_CONFIG_ENV_NAME,
    Action,
    AuthorizationError,
    Client,
    HTTPPort,
    JobDescription,
    JobPriority,
    JobRestartPolicy,
    JobStatus,
    Permission,
    RemoteImage,
)

from .ael import print_job_result, process_attach, process_exec, process_logs
from .click_types import (
    CLUSTER,
    JOB,
    JOB_COLUMNS,
    JOB_NAME,
    LOCAL_REMOTE_PORT,
    ORG,
    PRESET,
    PROJECT,
    TOP_COLUMNS,
    RemoteImageType,
)
from .const import EX_PLATFORMERROR
from .formatters.images import DockerImageProgress
from .formatters.jobs import (
    BaseJobsFormatter,
    JobStartProgress,
    JobStatusFormatter,
    JobTelemetryFormatter,
    LifeSpanUpdateFormatter,
    SimpleJobsFormatter,
    TabularJobsFormatter,
)
from .formatters.utils import (
    URIFormatter,
    get_datetime_formatter,
    image_formatter,
    uri_formatter,
)
from .parse_utils import (
    JobTableFormat,
    get_default_ps_columns,
    get_default_top_columns,
    parse_ps_columns,
    parse_sort_keys,
    parse_timedelta,
    parse_top_columns,
    serialize_timedelta,
)
from .root import Root
from .utils import (
    argument,
    calc_life_span,
    command,
    group,
    option,
    resolve_disk,
    resolve_job,
    resolve_job_ex,
    volume_to_verbose_str,
)

log = logging.getLogger(__name__)

STORAGE_MOUNTPOINT = "/var/storage"

DEFAULT_JOB_LIFE_SPAN = "1d"

TOP_REFRESH_DELAY = 0.2
TOP_NEW_JOBS_DELAY = 3


TTY_OPT = option(
    "-t/-T",
    "--tty/--no-tty",
    is_flag=True,
    default=None,
    help=(
        "Allocate a TTY, can be useful for interactive jobs. "
        "By default is on if the command is executed from a terminal, "
        "non-tty mode is used if executed from a script."
    ),
)


@group()
def job() -> None:
    """
    Job operations.
    """


@command(context_settings={"allow_interspersed_args": False})
@argument("job", type=JOB)
@argument("cmd", nargs=-1, type=click.UNPROCESSED, metavar="-- CMD...", required=True)
@TTY_OPT
async def exec(
    root: Root,
    job: str,
    tty: bool | None,
    cmd: Sequence[str],
) -> None:
    """
    Execute command in a running job.

    Examples:

    # Provides a shell to the container:
    apolo exec my-job -- /bin/bash

    # Executes a single command in the container and returns the control:
    apolo exec --no-tty my-job -- ls -l
    """
    cmd = _fix_cmd("apolo exec", "JOB -- CMD...", cmd)
    real_cmd = _parse_cmd(cmd)
    job, cluster_name = await resolve_job_ex(
        job,
        client=root.client,
        status=JobStatus.active_items(),
    )
    if tty is None:
        tty = root.tty
    _check_tty(root, tty)
    await process_exec(root, job, real_cmd, tty, cluster_name=cluster_name)


@command()
@argument("job", type=JOB)
@argument(
    "local_remote_port",
    type=LOCAL_REMOTE_PORT,
    nargs=-1,
    required=True,
    metavar="LOCAL_PORT:REMOTE_RORT...",
)
async def port_forward(
    root: Root, job: str, local_remote_port: list[tuple[int, int]]
) -> None:
    """
    Forward port(s) of a job.

    Forwards port(s) of a running job to local port(s).

    Examples:

    # Forward local port 2080 to port 80 of job's container.
    # You can use http://localhost:2080 in browser to access job's served http
    apolo job port-forward my-fastai-job 2080:80

    # Forward local port 2222 to job's port 22
    # Then copy all data from container's folder '/data' to current folder
    # (please run second command in other terminal)
    apolo job port-forward my-job-with-ssh-server 2222:22
    rsync -avxzhe "ssh -p 2222" root@localhost:/data .

    # Forward few ports at once
    apolo job port-forward my-job 2080:80 2222:22 2000:100

    """
    job_id, cluster_name = await resolve_job_ex(
        job,
        client=root.client,
        status=JobStatus.active_items(),
    )
    async with AsyncExitStack() as stack:
        for local_port, job_port in local_remote_port:
            root.print(
                f"Port localhost:{local_port} will be forwarded "
                f"to port {job_port} of {job_id}"
            )
            await stack.enter_async_context(
                root.client.jobs.port_forward(
                    job_id, local_port, job_port, cluster_name=cluster_name
                )
            )

        root.print("Press ^C to stop forwarding")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass


@command()
@argument("job", type=JOB)
@option(
    "--since",
    metavar="DATE_OR_TIMEDELTA",
    help="Only return logs after a specific date (including). "
    "Use value of format '1d2h3m4s' to specify moment in "
    "past relatively to current time.",
)
@option(
    "--timestamps",
    is_flag=True,
    help="Include timestamps on each line in the log output.",
)
async def logs(root: Root, since: str, job: str, timestamps: bool) -> None:
    """
    Print the logs for a job.
    """
    id, cluster_name = await resolve_job_ex(
        job,
        client=root.client,
        status=JobStatus.items(),
    )
    await process_logs(
        root,
        id,
        None,
        cluster_name=cluster_name,
        since=_parse_date(since),
        timestamps=timestamps,
    )
    if not root.quiet:
        status = await root.client.jobs.status(id)
        print_job_result(root, status)


@command()
@argument("job", type=JOB)
@option(
    "--port-forward",
    type=LOCAL_REMOTE_PORT,
    multiple=True,
    metavar="LOCAL_PORT:REMOTE_RORT",
    help="Forward port(s) of a running job to local port(s) "
    "(use multiple times for forwarding several ports)",
)
async def attach(root: Root, job: str, port_forward: list[tuple[int, int]]) -> None:
    """
    Attach terminal to a job

    Attach local standard input, output, and error streams to a running job.
    """
    id = await resolve_job(
        job,
        client=root.client,
        status=JobStatus.items(),
    )
    status = await root.client.jobs.status(id)
    if status.status.is_pending:
        with JobStartProgress.create(root.console, quiet=root.quiet) as progress:
            progress.step(status)
            while status.status.is_pending:
                await asyncio.sleep(0.2)
                status = await root.client.jobs.status(id)
                progress.step(status)

    tty = status.container.tty
    _check_tty(root, tty)

    await process_attach(
        root,
        status,
        tty=tty,
        logs=False,
        port_forward=port_forward,
    )


@command()
@option(
    "-s",
    "--status",
    multiple=True,
    type=click.Choice([item.value for item in JobStatus if item != JobStatus.UNKNOWN]),
    help="Filter out jobs by status (multiple option).",
)
@option(
    "--cluster",
    type=CLUSTER,
    help="Show jobs on a specified cluster (the current cluster by default).",
)
@option(
    "--org",
    type=ORG,
    help="Filter out jobs by org name "
    "(multiple option, the current org by default).",
    multiple=True,
)
@option("--all-orgs", is_flag=True, default=False, help="Show jobs in all orgs.")
@option(
    "-p",
    "--project",
    type=PROJECT,
    help="Filter out jobs by project name "
    "(multiple option, the current project by default).",
    multiple=True,
)
@option(
    "--all-projects", is_flag=True, default=False, help="Show jobs in all projects."
)
@option(
    "-o",
    "--owner",
    multiple=True,
    help="Filter out jobs by owner (multiple option). "
    "Supports `ME` option to filter by the current user.",
    secure=True,
)
@option("-n", "--name", metavar="NAME", help="Filter out jobs by name.", secure=True)
@option(
    "--distinct",
    is_flag=True,
    default=False,
    help="Show only first job if names are same.",
)
@option(
    "--recent-first/--recent-last",
    is_flag=True,
    default=False,
    help="Show newer jobs first or last",
)
@option(
    "-t",
    "--tag",
    metavar="TAG",
    type=str,
    help="Filter out jobs by tag (multiple option)",
    multiple=True,
)
@option(
    "-d",
    "--description",
    metavar="DESCRIPTION",
    default="",
    help="Filter out jobs by description (exact match).",
    secure=True,
)
@option(
    "--since",
    metavar="DATE_OR_TIMEDELTA",
    help="Show jobs created after a specific date (including). "
    "Use value of format '1d2h3m4s' to specify moment in "
    "past relatively to current time.",
)
@option(
    "--until",
    metavar="DATE_OR_TIMEDELTA",
    help="Show jobs created before a specific date (including). "
    "Use value of format '1d2h3m4s' to specify moment in "
    "past relatively to current time.",
)
@option(
    "-a",
    "--all",
    is_flag=True,
    default=False,
    help="Show all jobs regardless the status.",
)
@option("-w", "--wide", is_flag=True, help="Do not cut long lines for terminal width.")
@option(
    "--format",
    type=JOB_COLUMNS,
    help=(
        'Output table format, see "apolo help ps-format" '
        "for more info about the format specification. "
        "The default can be changed using the job.ps-format "
        'configuration variable documented in "apolo help user-config"'
    ),
    default=None,
)
@option("--full-uri", is_flag=True, help="Output full image URI.")
async def ls(
    root: Root,
    status: Sequence[str],
    all: bool,
    cluster: str,
    org: Sequence[str],
    all_orgs: bool,
    project: Sequence[str],
    all_projects: bool,
    name: str,
    distinct: bool,
    recent_first: bool,
    tag: Sequence[str],
    owner: Sequence[str],
    since: str,
    until: str,
    description: str,
    wide: bool,
    format: JobTableFormat | None,
    full_uri: bool,
) -> None:
    """
    List all jobs.

    Examples:

    apolo ps -a
    apolo ps -a --owner=user-1 --owner=user-2
    apolo ps --name my-experiments-v1 -s failed -s succeeded
    apolo ps --description="my favourite job"
    apolo ps -s failed -s succeeded -q
    apolo ps -t tag1 -t tag2
    """

    format = await calc_ps_columns(root.client, format)

    statuses = calc_statuses(status, all)
    owners = set(owner)
    if "ME" in owners:
        owners.remove("ME")
        owners.add(root.client.config.username)
    tags = set(tag)
    if not cluster:
        cluster = root.client.config.cluster_name

    if all_orgs:
        org_names: list[str] = []
    else:
        org_names = list(org)

    if all_projects:
        project_names: Sequence[str] = []
    else:
        project_names = project or [root.client.config.project_name_or_raise]

    uri_fmtr: URIFormatter
    if full_uri:
        uri_fmtr = str
    else:
        uri_fmtr = uri_formatter(
            project_name=root.client.config.project_name_or_raise,
            cluster_name=root.client.cluster_name,
            org_name=root.client.config.org_name,
        )
    if root.quiet:
        formatter: BaseJobsFormatter = SimpleJobsFormatter()
    else:
        image_fmtr = image_formatter(uri_formatter=uri_fmtr)
        formatter = TabularJobsFormatter(
            root.client.username,
            format,
            image_formatter=image_fmtr,
            datetime_formatter=get_datetime_formatter(root.iso_datetime_format),
        )

    async with root.client.jobs.list(
        statuses=statuses,
        name=name,
        owners=owners,
        tags=tags,
        since=_parse_date(since),
        until=_parse_date(until),
        reverse=recent_first,
        cluster_name=cluster,
        org_names=org_names,
        project_names=project_names,
    ) as jobs:
        # client-side filtering
        if description:
            jobs = (job async for job in jobs if job.description == description)

        if distinct:

            async def _filter_distinct(
                jobs_iter: AsyncIterator[JobDescription],
            ) -> AsyncIterator[JobDescription]:
                names: set[str] = set()
                async for job in jobs_iter:
                    if job.name in names:
                        continue
                    if job.name is not None:
                        names.add(job.name)
                    yield job

            jobs = _filter_distinct(jobs)

        with root.status("Fetching jobs") as rich_status:
            jobs_list = []
            async for job in jobs:
                jobs_list.append(job)
                rich_status.update(f"Fetching jobs ({len(jobs_list)} loaded)")

    with root.pager():
        root.print(formatter(jobs_list))


@command()
@argument("job", type=JOB)
@option("--full-uri", is_flag=True, help="Output full URI.")
async def status(root: Root, job: str, full_uri: bool) -> None:
    """
    Display status of a job.
    """
    id = await resolve_job(
        job,
        client=root.client,
        status=JobStatus.items(),
    )
    res = await root.client.jobs.status(id)
    uri_fmtr: URIFormatter
    if full_uri:
        uri_fmtr = str
    else:
        uri_fmtr = uri_formatter(
            project_name=root.client.config.project_name_or_raise,
            cluster_name=root.client.cluster_name,
            org_name=root.client.config.org_name,
        )
    root.print(
        JobStatusFormatter(
            uri_formatter=uri_fmtr,
            datetime_formatter=get_datetime_formatter(root.iso_datetime_format),
        )(res)
    )


@command()
@argument("job", type=JOB)
@argument(
    "additional-life-span",
    type=str,
    metavar="TIMEDELTA",
)
async def bump_life_span(root: Root, job: str, additional_life_span: str) -> None:
    """
    Increase job life span
    """
    job_id = await resolve_job(
        job,
        client=root.client,
        status=JobStatus.items(),
    )
    await root.client.jobs.bump_life_span(
        id=job_id,
        additional_life_span=parse_timedelta(additional_life_span).total_seconds(),
    )
    if not root.quiet:
        res = await root.client.jobs.status(id=job_id)
        root.print(
            LifeSpanUpdateFormatter(
                datetime_formatter=get_datetime_formatter(root.iso_datetime_format),
            )(res)
        )


@command()
@click.argument("job", type=JOB)
async def browse(root: Root, job: str) -> None:
    """
    Opens a job's URL in a web browser.
    """
    id = await resolve_job(job, client=root.client, status=JobStatus.active_items())
    res = await root.client.jobs.status(id)
    await browse_job(root, res)


@command()
@argument("jobs", nargs=-1, required=False, type=JOB)
@option(
    "--cluster",
    type=CLUSTER,
    help="Show jobs on a specified cluster (the current cluster by default).",
)
@option(
    "-o",
    "--owner",
    multiple=True,
    help="Filter out jobs by owner (multiple option). "
    "Supports `ME` option to filter by the current user. "
    "Specify `ALL` to show jobs of all users.",
    secure=True,
)
@option("-n", "--name", metavar="NAME", help="Filter out jobs by name.", secure=True)
@option(
    "-t",
    "--tag",
    metavar="TAG",
    type=str,
    help="Filter out jobs by tag (multiple option)",
    multiple=True,
)
@option(
    "-d",
    "--description",
    metavar="DESCRIPTION",
    default="",
    help="Filter out jobs by description (exact match).",
    secure=True,
)
@option(
    "--since",
    metavar="DATE_OR_TIMEDELTA",
    help="Show jobs created after a specific date (including). "
    "Use value of format '1d2h3m4s' to specify moment in "
    "past relatively to current time.",
)
@option(
    "--until",
    metavar="DATE_OR_TIMEDELTA",
    help="Show jobs created before a specific date (including). "
    "Use value of format '1d2h3m4s' to specify moment in "
    "past relatively to current time.",
)
@option(
    "--sort",
    metavar="COLUMNS",
    help="Sort rows by specified column. "
    'Add "-" prefix to revert the sorting order. '
    "Multiple columns can be specified (comma separated).",
    default="cpu",
    show_default=True,
)
@option(
    "--format",
    type=TOP_COLUMNS,
    help=(
        'Output table format, see "apolo help top-format" '
        "for more info about the format specification. "
        "The default can be changed using the job.top-format "
        'configuration variable documented in "apolo help user-config"'
    ),
    default=None,
)
@option("--full-uri", is_flag=True, help="Output full image URI.")
@option(
    "--timeout",
    default=0,
    type=float,
    show_default=True,
    help="Maximum allowed time for executing the command, 0 for no timeout",
)
@option(
    "-p",
    "--project",
    type=PROJECT,
    help="Filter out jobs by project name (multiple option).",
    multiple=True,
)
async def top(
    root: Root,
    jobs: Sequence[str],
    cluster: str,
    name: str,
    tag: Sequence[str],
    owner: Sequence[str],
    since: str,
    until: str,
    description: str,
    sort: str,
    format: JobTableFormat | None,
    full_uri: bool,
    timeout: float,
    project: Sequence[str],
) -> None:
    """
    Display GPU/CPU/Memory usage.

    Examples:

    apolo top
    apolo top job-1 job-2
    apolo top --owner=user-1 --owner=user-2
    apolo top --name my-experiments-v1
    apolo top -t tag1 -t tag2
    """

    sort_keys = parse_sort_keys(sort)
    format = await calc_top_columns(root.client, format)
    if not cluster:
        cluster = root.client.config.cluster_name

    observed: set[str] = set()
    loop = asyncio.get_event_loop()

    if jobs:
        for opt, val in [
            ("name", name),
            ("owner", owner),
            ("since", since),
            ("until", until),
            ("description", description),
            ("project", project),
        ]:
            if val:
                raise click.UsageError(
                    f"Option --{opt} is mutually exclusive with job arguments"
                )

        async def create_pollers() -> None:
            for job_str in jobs:
                job_id = await resolve_job(
                    job_str, client=root.client, status=JobStatus.active_items()
                )
                if job_id in observed:
                    continue
                observed.add(job_id)
                job = await root.client.jobs.status(job_id)
                loop.create_task(poller(job))

    else:
        owners = set(owner)
        if not owners:
            owners = {root.client.config.username}
        elif "ALL" in owners:
            owners.remove("ALL")
            if owners:
                raise click.UsageError(
                    "Multiple --owner options are incompatible with --owner=ALL"
                )
        elif "ME" in owners:
            owners.remove("ME")
            owners.add(root.client.config.username)
        tags = set(tag)
        since_dt = _parse_date(since)
        until_dt = _parse_date(until)

        async def create_pollers() -> None:
            nonlocal since_dt
            while True:
                async with root.client.jobs.list(
                    statuses=JobStatus.active_items(),
                    name=name,
                    owners=owners,
                    tags=tags,
                    since=since_dt,
                    until=until_dt,
                    cluster_name=cluster,
                    project_names=project,
                ) as jobs:
                    # client-side filtering
                    if description:
                        jobs = (
                            job async for job in jobs if job.description == description
                        )

                    dt: datetime | None
                    dt = datetime.now(timezone.utc) - timedelta(minutes=1)
                    if since_dt is None or since_dt < dt:
                        since_dt = dt
                    async for job in jobs:
                        job_id = job.id
                        if job_id in observed:
                            continue
                        observed.add(job_id)
                        dt = job.history.created_at
                        if dt is not None and since_dt < dt:
                            since_dt = dt
                        loop.create_task(poller(job))
                await asyncio.sleep(TOP_NEW_JOBS_DELAY)

    async def poller(job: JobDescription) -> None:
        try:
            async with root.client.jobs.top(
                job.id, cluster_name=job.cluster_name
            ) as it:
                async for info in it:
                    formatter.update(job, info)
                    await asyncio.sleep(0)
        except ValueError:
            pass  # Job is finished.
        finally:
            formatter.remove(job.id)
        await asyncio.sleep(0)

    async def renderer() -> None:
        async with async_timeout.timeout(timeout if timeout else None):
            while True:
                if formatter.changed:
                    formatter.render()
                await asyncio.sleep(TOP_REFRESH_DELAY)

    uri_fmtr: URIFormatter
    if full_uri:
        uri_fmtr = str
    else:
        uri_fmtr = uri_formatter(
            project_name=root.client.config.project_name_or_raise,
            cluster_name=root.client.cluster_name,
            org_name=root.client.config.org_name,
        )
    image_fmtr = image_formatter(uri_formatter=uri_fmtr)
    datetime_fmtr = get_datetime_formatter(root.iso_datetime_format)

    with JobTelemetryFormatter(
        root.console,
        root.client.username,
        sort_keys=sort_keys,
        columns=format,
        image_formatter=image_fmtr,
        datetime_formatter=datetime_fmtr,
    ) as formatter:
        await asyncio.gather(create_pollers(), renderer())


@command()
@argument("job", type=JOB)
@argument("image", type=RemoteImageType())
async def save(root: Root, job: str, image: RemoteImage) -> None:
    """
    Save job's state to an image.

    Examples:
    apolo job save job-id image:ubuntu-patched
    apolo job save my-favourite-job image:ubuntu-patched:v1
    apolo job save my-favourite-job image://bob/ubuntu-patched
    """
    id, cluster_name = await resolve_job_ex(
        job,
        client=root.client,
        status=JobStatus.items(),
    )
    progress = DockerImageProgress.create(console=root.console, quiet=root.quiet)
    with contextlib.closing(progress):
        await root.client.jobs.save(
            id, image, progress=progress, cluster_name=cluster_name
        )
    root.print(image)


@command()
@argument("jobs", nargs=-1, required=True, type=JOB)
async def kill(root: Root, jobs: Sequence[str]) -> None:
    """
    Kill job(s).
    """
    errors = []
    for job in jobs:
        job_resolved = await resolve_job(
            job, client=root.client, status=JobStatus.active_items()
        )
        try:
            await root.client.jobs.kill(job_resolved)
            # TODO (ajuszkowski) printing should be on the cli level
            root.print(job_resolved)
        except ValueError as e:
            errors.append((job, e))
        except AuthorizationError:
            errors.append((job, ValueError(f"Not enough permissions")))

    for job, error in errors:
        root.print(f"Cannot kill job {job}: {error}", err=True, style="red")
    if errors:
        sys.exit(1)


@command(context_settings={"allow_interspersed_args": False})
@argument("image", type=RemoteImageType())
@argument("cmd", nargs=-1, type=click.UNPROCESSED, metavar="[-- CMD...]")
@option(
    "--cluster",
    type=CLUSTER,
    help="Run job in a specified cluster",
    default=None,
)
@option(
    "--org",
    type=ORG,
    help="Run job in a specified org",
    default=None,
)
@option(
    "-s",
    "--preset",
    type=PRESET,
    metavar="PRESET",
    help=(
        "Predefined resource configuration (to see available values, "
        "run `apolo config show`)"
    ),
)
@option(
    "-x/-X",
    "--extshm/--no-extshm",
    is_flag=True,
    default=True,
    show_default=True,
    help="Request extended '/dev/shm' space",
)
@option(
    "--http",
    type=int,
    metavar="PORT",
    default=None,
    help="Enable HTTP port forwarding to container (use --http-port instead)",
    hidden=True,
)
@option(
    "--http-port",
    type=int,
    metavar="PORT",
    default=80,
    show_default=True,
    help="Enable HTTP port forwarding to container",
)
@option(
    "--http-auth/--no-http-auth",
    is_flag=True,
    help="Enable HTTP authentication for forwarded HTTP port  [default: True]",
    default=None,
)
@option(
    "-n",
    "--name",
    metavar="NAME",
    type=JOB_NAME,
    help="Optional job name",
    default=None,
    secure=True,
)
@option(
    "--tag",
    metavar="TAG",
    type=str,
    help="Optional job tag, multiple values allowed",
    multiple=True,
)
@option(
    "-d",
    "--description",
    metavar="DESC",
    help="Optional job description in free format",
    secure=True,
)
@option(
    "-v",
    "--volume",
    metavar="MOUNT",
    multiple=True,
    help=(
        "Mounts directory from vault into container. "
        "Use multiple options to mount more than one volume. "
        "See `apolo help secrets` for information about "
        "passing secrets as mounted files."
    ),
    secure=True,
)
@option(
    "--entrypoint",
    type=str,
    help=(
        "Executable entrypoint in the container "
        "(note that it overwrites `ENTRYPOINT` and `CMD` "
        "instructions of the docker image)"
    ),
    secure=True,
)
@option(
    "-w",
    "--workdir",
    type=str,
    help="Working directory inside the container",
    secure=True,
)
@option(
    "-e",
    "--env",
    metavar="VAR=VAL",
    multiple=True,
    help=(
        "Set environment variable in container. "
        "Use multiple options to define more than one variable. "
        "See `apolo help secrets` for information about "
        "passing secrets as environment variables."
    ),
    secure=True,
)
@option(
    "--env-file",
    type=click.Path(exists=True),
    multiple=True,
    help="File with environment variables to pass",
    secure=True,
)
@option(
    "--restart",
    default="never",
    show_default=True,
    type=click.Choice([str(i) for i in JobRestartPolicy]),
    help="Restart policy to apply when a job exits",
)
@option(
    "--life-span",
    type=str,
    metavar="TIMEDELTA",
    help=(
        "Optional job run-time limit in the format '1d2h3m4s' "
        "(some parts may be missing). Set '0' to disable. "
        "Default value '1d' can be changed in the user config."
    ),
    show_default=True,
)
@option(
    "--schedule-timeout",
    type=str,
    metavar="TIMEDELTA",
    help=(
        "Optional job schedule timeout in the format '3m4s' "
        "(some parts may be missing)."
    ),
    show_default=True,
)
@option(
    "--wait-start/--no-wait-start",
    default=True,
    show_default=True,
    help="Wait for a job start or failure",
)
@option(
    "--pass-config/--no-pass-config",
    default=False,
    show_default=True,
    help="Upload apolo config to the job",
)
@option(
    "--wait-for-seat/--no-wait-for-seat",
    default=False,
    show_default=True,
    help="Wait for total running jobs quota",
)
@option(
    "--port-forward",
    type=LOCAL_REMOTE_PORT,
    multiple=True,
    metavar="LOCAL_PORT:REMOTE_RORT",
    help="Forward port(s) of a running job to local port(s) "
    "(use multiple times for forwarding several ports)",
)
@option("--browse", is_flag=True, help="Open a job's URL in a web browser")
@option(
    "--detach",
    is_flag=True,
    help="Don't attach to job logs and don't wait for exit code",
)
@option(
    "--privileged",
    is_flag=True,
    default=False,
    show_default=True,
    help="Run job in privileged mode, if it is supported by cluster.",
)
@option(
    "--share",
    metavar="USER",
    multiple=True,
    help=("Share job write permissions to user or role."),
)
@option(
    "--priority",
    type=click.Choice([p.name.lower() for p in JobPriority]),
    help="Priority used to specify job's start order. "
    "Jobs with higher priority will start before ones with lower priority. "
    "Priority should be supported by cluster.",
)
@option(
    "--energy-schedule",
    metavar="NAME",
    help=(
        "Run job only within a selected energy schedule. "
        "Selected preset should have scheduler enabled."
    ),
)
@option(
    "-p",
    "--project",
    type=PROJECT,
    help="Run job in a specified project.",
    default=None,
)
@TTY_OPT
async def run(
    root: Root,
    image: RemoteImage,
    preset: str,
    cluster: str | None,
    org: str | None,
    extshm: bool,
    http: int | None,
    http_port: int,
    http_auth: bool | None,
    entrypoint: str | None,
    cmd: Sequence[str],
    workdir: str | None,
    volume: Sequence[str],
    env: Sequence[str],
    env_file: Sequence[str],
    restart: str,
    life_span: str | None,
    name: str | None,
    tag: Sequence[str],
    description: str | None,
    wait_start: bool,
    pass_config: bool,
    wait_for_seat: bool,
    port_forward: list[tuple[int, int]],
    browse: bool,
    detach: bool,
    tty: bool | None,
    schedule_timeout: str | None,
    privileged: bool,
    share: Sequence[str],
    priority: str | None,
    energy_schedule: str | None,
    project: str | None,
) -> None:
    """
    Run a job

    IMAGE docker image name to run in a job.

    CMD list will be passed as arguments to the executed job's image.

    Examples:

    # Starts a container pytorch/pytorch:latest on a machine with smaller GPU resources
    # (see exact values in `apolo config show`) and with two volumes mounted:
    #   storage:/<home-directory>   --> /var/storage/home (in read-write mode),
    #   storage:/neuromation/public --> /var/storage/neuromation (in read-only mode).
    apolo run --preset=gpu-small --volume=storage::/var/storage/home:rw \\\\
        --volume=storage:/neuromation/public:/var/storage/home:ro pytorch/pytorch:latest

    # Starts a container using the custom image my-ubuntu:latest stored in apolo
    # registry, run /script.sh and pass arg1 and arg2 as its arguments:
    apolo run -s cpu-small --entrypoint=/script.sh image:my-ubuntu:latest -- arg1 arg2
    """
    if http is not None:
        root.console.print("[red]--http option is deprecated,", markup=True)
        root.console.print(
            "[red]Please use  --http-port option instead of --http", markup=True
        )
        http_port = http
    cmd = _fix_cmd("apolo run", "IMAGE -- CMD...", cmd)
    cluster_name = cluster or root.client.cluster_name
    org_name = org
    cluster_config = root.client.config.clusters[cluster_name]
    if not preset:
        preset = next(iter(cluster_config.presets.keys()))
    log.info(f"Using preset '{preset}'")
    if tty is None:
        tty = root.tty
    await run_job(
        root,
        image=image,
        preset=preset,
        extshm=extshm,
        http_port=http_port,
        http_auth=http_auth,
        entrypoint=entrypoint,
        cmd=cmd,
        working_dir=workdir,
        volume=volume,
        env=env,
        env_file=env_file,
        restart=restart,
        life_span=life_span,
        port_forward=port_forward,
        name=name,
        tags=tag,
        description=description,
        wait_start=wait_start,
        pass_config=pass_config,
        wait_for_jobs_quota=wait_for_seat,
        browse=browse,
        detach=detach,
        tty=tty,
        schedule_timeout=schedule_timeout,
        privileged=privileged,
        share=share,
        cluster_name=cluster_name,
        org_name=org_name,
        priority=priority,
        energy_schedule_name=energy_schedule,
        project_name=project,
    )


@command()
@argument("job", type=JOB)
async def generate_run_command(root: Root, job: str) -> None:
    """
    Generate command that will rerun given job.

    Examples:

    # You can use the following to directly re-execute it:
    eval $(apolo job generate-run-command <job-id>)
    """
    id = await resolve_job(
        job,
        client=root.client,
        status=JobStatus.items(),
    )
    job_description = await root.client.jobs.status(id)
    args = _job_to_cli_args(job_description)
    root.print("apolo run " + " ".join(args), soft_wrap=True)


job.add_command(run)
job.add_command(generate_run_command)
job.add_command(ls)
job.add_command(status)
job.add_command(exec)
job.add_command(port_forward)
job.add_command(logs)
job.add_command(kill)
job.add_command(top)
job.add_command(save)
job.add_command(browse)
job.add_command(attach)
job.add_command(bump_life_span)


async def run_job(
    root: Root,
    *,
    image: RemoteImage,
    preset: str,
    extshm: bool,
    http_port: int | None,
    http_auth: bool | None,
    entrypoint: str | None,
    cmd: Sequence[str],
    working_dir: str | None,
    volume: Sequence[str],
    env: Sequence[str],
    env_file: Sequence[str],
    restart: str,
    life_span: str | None,
    port_forward: list[tuple[int, int]],
    name: str | None,
    tags: Sequence[str],
    description: str | None,
    wait_start: bool,
    pass_config: bool,
    wait_for_jobs_quota: bool,
    browse: bool,
    detach: bool,
    tty: bool,
    schedule_timeout: str | None,
    privileged: bool,
    share: Sequence[str],
    cluster_name: str,
    org_name: str | None,
    priority: str | None,
    energy_schedule_name: str | None,
    project_name: str | None,
) -> JobDescription:
    if http_auth is None:
        http_auth = True
    elif not http_port:
        if http_auth:
            raise click.UsageError("--http-auth requires --http-port")
        else:
            raise click.UsageError("--no-http-auth requires --http-port")
    if browse and not http_port:
        raise click.UsageError("--browse requires --http-port")
    if browse and not wait_start:
        raise click.UsageError("Cannot use --browse and --no-wait-start together")
    if not wait_start:
        detach = True
    if not detach:
        _check_tty(root, tty)

    job_restart_policy = JobRestartPolicy(restart)
    log.debug(f"Job restart policy: {job_restart_policy}")

    job_life_span = await calc_life_span(
        root.client, life_span, DEFAULT_JOB_LIFE_SPAN, "job"
    )
    log.debug(f"Job run-time limit: {job_life_span}")

    if schedule_timeout is None:
        job_schedule_timeout = None
    else:
        job_schedule_timeout = parse_timedelta(schedule_timeout).total_seconds()
    log.debug(f"Job schedule timeout: {job_schedule_timeout}")

    env_parse_result = root.client.parse.envs(env, env_file, cluster_name=cluster_name)
    env_dict, secret_env_dict = env_parse_result.env, env_parse_result.secret_env
    real_cmd = _parse_cmd(cmd)

    log.debug(f'entrypoint="{entrypoint}"')
    log.debug(f'cmd="{real_cmd}"')

    log.info(f"Using image '{image}'")

    volume_parse_result = root.client.parse.volumes(volume, cluster_name=cluster_name)
    volumes = list(volume_parse_result.volumes)
    secret_files = volume_parse_result.secret_files

    # Replace disk names with disk ids
    async def _force_disk_id(disk_uri: URL) -> URL:
        disk_id = await resolve_disk(
            disk_uri, client=root.client, cluster_name=cluster_name
        )
        return disk_uri / f"../{disk_id}"

    disk_volumes = [
        dataclasses.replace(
            disk_volume, disk_uri=await _force_disk_id(disk_volume.disk_uri)
        )
        for disk_volume in volume_parse_result.disk_volumes
    ]

    if pass_config:
        env_name = PASS_CONFIG_ENV_NAME
        if env_name in env_dict:
            raise ValueError(f"{env_name} is already set to {env_dict[env_name]}")

    if volumes:
        log.info(
            "Using volumes: \n"
            + "\n".join(f"  {volume_to_verbose_str(v)}" for v in volumes)
        )

    job_priority = JobPriority[priority.upper()] if priority else None

    if not project_name:
        project_name = root.client.config.project_name

    job = await root.client.jobs.start(
        image=image,
        preset_name=preset,
        cluster_name=cluster_name,
        org_name=org_name,
        entrypoint=entrypoint,
        command=real_cmd,
        working_dir=working_dir,
        http=HTTPPort(http_port, http_auth) if http_port else None,
        env=env_dict,
        volumes=volumes,
        secret_env=secret_env_dict,
        secret_files=secret_files,
        disk_volumes=disk_volumes,
        tty=tty,
        shm=extshm,
        pass_config=pass_config,
        wait_for_jobs_quota=wait_for_jobs_quota,
        name=name,
        tags=tags,
        description=description,
        restart_policy=job_restart_policy,
        life_span=job_life_span,
        schedule_timeout=job_schedule_timeout,
        privileged=privileged,
        priority=job_priority,
        energy_schedule_name=energy_schedule_name,
        project_name=project_name,
    )
    permission = Permission(job.uri, Action.WRITE)
    for user in share:
        await root.client.users.share(user, permission)
    with JobStartProgress.create(console=root.console, quiet=root.quiet) as progress:
        progress.begin(job)
        while wait_start and job.status.is_pending:
            await asyncio.sleep(0.2)
            job = await root.client.jobs.status(job.id)
            progress.step(job)
        progress.end(job)

    # Even if we detached, but the job has failed to start
    # (most common reason - no resources), the command fails
    if job.status == JobStatus.FAILED:
        sys.exit(job.history.exit_code or EX_PLATFORMERROR)

    if browse:
        await browse_job(root, job)

    if not detach:
        await process_attach(
            root,
            job,
            tty=tty,
            logs=True,
            port_forward=port_forward,
        )

    return job


def _parse_cmd(cmd: Sequence[str]) -> str:
    if len(cmd) == 1:
        real_cmd = cmd[0]
    else:
        real_cmd = " ".join(shlex.quote(arg) for arg in cmd)
    return real_cmd


async def browse_job(root: Root, job: JobDescription) -> None:
    url = job.http_url
    if url.scheme not in ("http", "https"):
        raise RuntimeError(f"Cannot browse job URL: {url}")
    root.print(f"Browsing job, please open: {url}")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, webbrowser.open, str(url))


def calc_statuses(status: Sequence[str], all: bool) -> set[JobStatus]:
    statuses = set(status)
    if all:
        if statuses:
            opt = " ".join(f"--status={s}" for s in status)
            log.warning(f"Option `-a/--all` overwrites option(s) `{opt}`")
        statuses = set()
    elif not statuses:
        statuses = {item.value for item in JobStatus.active_items()}

    return {JobStatus(s) for s in statuses}


async def calc_ps_columns(
    client: Client, format: JobTableFormat | None
) -> JobTableFormat:
    if format is None:
        config = await client.config.get_user_config()
        section = config.get("job")
        if section is not None:
            format_str = section.get("ps-format")
            if format_str is not None:
                return parse_ps_columns(format_str)
        return get_default_ps_columns()
    return format


async def calc_top_columns(
    client: Client, format: JobTableFormat | None
) -> JobTableFormat:
    if format is None:
        config = await client.config.get_user_config()
        section = config.get("job")
        if section is not None:
            format_str = section.get("top-format")
            if format_str is not None:
                return parse_top_columns(format_str)
        return get_default_top_columns()
    return format


def _parse_date(value: str) -> datetime | None:
    if value:
        try:
            return isoparse(value)
        except ValueError:
            try:
                delta = parse_timedelta(value)
                return datetime.now(timezone.utc) - delta
            except click.UsageError:
                raise ValueError(
                    "Date should be either in ISO-8601 format or "
                    "relative delta of form 1d2h3m4s"
                )
    else:
        return None


def _check_tty(root: Root, tty: bool) -> None:
    if tty and not root.tty:
        raise RuntimeError(
            "The operation should be executed from a terminal, "
            "the input device is not a TTY"
        )


def _job_to_cli_args(job: JobDescription) -> list[str]:
    res = []
    if job.preset_name:
        res += ["--preset", job.preset_name]
    else:
        log.warning("Cannot determine preset name used to run job")
    if not job.container.resources.shm:
        res += ["--no-extshm"]
    if job.container.http:
        if job.container.http.port != 80:
            res += ["--http-port", str(job.container.http.port)]
        if not job.container.http.requires_auth:
            res += ["--no-http-auth"]
    if job.name:
        res += ["--name", job.name]
    for tag in job.tags:
        res += ["--tag", tag]
    if job.description:
        res += ["--description", shlex.quote(job.description)]
    for volume in job.container.volumes:
        res += [
            "--volume",
            (
                f"{volume.storage_uri}:{volume.container_path}"
                f":{'ro' if volume.read_only else 'rw'}"
            ),
        ]
    for disk in job.container.disk_volumes:
        res += [
            "--volume",
            f"{disk.disk_uri}:{disk.container_path}:{'ro' if disk.read_only else 'rw'}",
        ]
    for secret in job.container.secret_files:
        res += ["--volume", f"{secret.secret_uri}:{secret.container_path}"]
    if job.container.entrypoint:
        res += ["--entrypoint", job.container.entrypoint]
    if job.container.working_dir:
        res += ["--workdir", job.container.working_dir]
    for env_name, env_value in job.container.env.items():
        if env_name == PASS_CONFIG_ENV_NAME and job.pass_config:
            continue  # Do not specify value for pass config env variable
        res += ["--env", f"{env_name}={env_value}"]
    for env_name, secret_uri in job.container.secret_env.items():
        res += ["--env", f"{env_name}={secret_uri}"]
    if job.restart_policy == JobRestartPolicy.ALWAYS:
        res += ["--restart", str(JobRestartPolicy.ALWAYS)]
    if job.restart_policy == JobRestartPolicy.ON_FAILURE:
        res += ["--restart", str(JobRestartPolicy.ON_FAILURE)]
    if job.life_span:
        res += ["--life-span", serialize_timedelta(timedelta(seconds=job.life_span))]
    if job.schedule_timeout:
        res += [
            "--schedule-timeout",
            serialize_timedelta(timedelta(seconds=job.schedule_timeout)),
        ]
    if job.pass_config:
        res += ["--pass-config"]
    if job.privileged:
        res += ["--privileged"]
    if job.priority != JobPriority.NORMAL:
        res += ["--priority", job.priority.name.lower()]
    if job.energy_schedule_name:
        res += ["--energy-schedule", job.energy_schedule_name]
    res += ["--project", job.project_name, str(job.container.image)]
    if job.container.command:
        res += ["--", job.container.command]
    return res


def _fix_cmd(cmd_name: str, tmpl: str, cmd: Sequence[str]) -> Sequence[str]:
    if cmd:
        if cmd[0] != "--":
            old_pre, sep, old_suff = tmpl.partition("--")
            old = old_pre.strip() + " " + old_suff.strip()
            log.warning(
                f"'{cmd_name} {old}' is DEPRECATED and will be removed "
                f"in a future version.\nUse '{cmd_name} {tmpl}' instead."
            )
        else:
            return cmd[1:]
    return cmd
