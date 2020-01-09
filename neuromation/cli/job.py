import asyncio
import contextlib
import logging
import os
import shlex
import sys
import textwrap
import uuid
import webbrowser
from typing import Dict, List, Optional, Sequence, Set, Tuple

import async_timeout
import click
import idna
from yarl import URL

from neuromation.api import (
    CONFIG_ENV_NAME,
    TRUSTED_CONFIG_PATH,
    AuthorizationError,
    Container,
    HTTPPort,
    JobDescription,
    JobStatus,
    RemoteImage,
    Resources,
    Volume,
)
from neuromation.cli.formatters import DockerImageProgress

from .const import EX_PLATFORMERROR
from .defaults import (
    GPU_MODELS,
    JOB_CPU_NUMBER,
    JOB_GPU_MODEL,
    JOB_GPU_NUMBER,
    JOB_MEMORY_AMOUNT,
)
from .formatters.jobs import (
    BaseJobsFormatter,
    JobFormatter,
    JobStartProgress,
    JobStatusFormatter,
    JobTelemetryFormatter,
    SimpleJobsFormatter,
    TabularJobsFormatter,
)
from .parse_utils import COLUMNS, JobColumnInfo
from .root import Root
from .utils import (
    JOB_COLUMNS,
    JOB_NAME,
    LOCAL_REMOTE_PORT,
    MEGABYTE,
    AsyncExitStack,
    ImageType,
    alias,
    async_cmd,
    command,
    deprecated_quiet_option,
    group,
    pager_maybe,
    resolve_job,
    volume_to_verbose_str,
)


log = logging.getLogger(__name__)

STORAGE_MOUNTPOINT = "/var/storage"
ROOT_MOUNTPOINT = "/var/neuro"

NEUROMATION_ROOT_ENV_VAR = "NEUROMATION_ROOT"
NEUROMATION_HOME_ENV_VAR = "NEUROMATION_HOME"
RESERVED_ENV_VARS = {NEUROMATION_ROOT_ENV_VAR, NEUROMATION_HOME_ENV_VAR}


def _get_neuro_mountpoint(username: str) -> str:
    return f"{ROOT_MOUNTPOINT}/{username}"


def build_env(env: Sequence[str], env_file: Optional[str]) -> Dict[str, str]:
    if env_file:
        with open(env_file, "r") as ef:
            env = ef.read().splitlines() + list(env)

    env_dict = {}
    for line in env:
        splitted = line.split("=", 1)
        name = splitted[0]
        if len(splitted) == 1:
            val = os.environ.get(splitted[0], "")
        else:
            val = splitted[1]
        if name in RESERVED_ENV_VARS:
            raise click.UsageError(
                f"Unable to re-define system-reserved environment variable: {name}"
            )
        env_dict[name] = val
    return env_dict


@group()
def job() -> None:
    """
    Job operations.
    """


@command(context_settings=dict(allow_interspersed_args=False))
@click.argument("image", type=ImageType())
@click.argument("cmd", nargs=-1, type=click.UNPROCESSED)
@click.option(
    "-g",
    "--gpu",
    metavar="NUMBER",
    type=int,
    help="Number of GPUs to request",
    default=JOB_GPU_NUMBER,
    show_default=True,
)
@click.option(
    "--gpu-model",
    metavar="MODEL",
    type=click.Choice(GPU_MODELS),
    help="GPU to use",
    default=JOB_GPU_MODEL,
    show_default=True,
)
@click.option("--tpu-type", metavar="TYPE", type=str, help="TPU type to use")
@click.option(
    "tpu_software_version",
    "--tpu-sw-version",
    metavar="VERSION",
    type=str,
    help="Requested TPU software version",
)
@click.option(
    "-c",
    "--cpu",
    metavar="NUMBER",
    type=float,
    help="Number of CPUs to request",
    default=JOB_CPU_NUMBER,
    show_default=True,
)
@click.option(
    "-m",
    "--memory",
    metavar="AMOUNT",
    type=MEGABYTE,
    help="Memory amount to request",
    default=JOB_MEMORY_AMOUNT,
    show_default=True,
)
@click.option(
    "-x/-X",
    "--extshm/--no-extshm",
    is_flag=True,
    default=True,
    show_default=True,
    help="Request extended '/dev/shm' space",
)
@click.option(
    "--http", type=int, metavar="PORT", help="Enable HTTP port forwarding to container"
)
@click.option(
    "--http-auth/--no-http-auth",
    is_flag=True,
    help="Enable HTTP authentication for forwarded HTTP port  [default: True]",
    default=None,
)
@click.option(
    "--preemptible/--non-preemptible",
    "-p/-P",
    help="Run job on a lower-cost preemptible instance",
    default=False,
    show_default=True,
)
@click.option(
    "-n",
    "--name",
    metavar="NAME",
    type=JOB_NAME,
    help="Optional job name",
    default=None,
)
@click.option(
    "-d",
    "--description",
    metavar="DESC",
    help="Optional job description in free format",
)
@deprecated_quiet_option
@click.option(
    "-v",
    "--volume",
    metavar="MOUNT",
    multiple=True,
    help="Mounts directory from vault into container. "
    "Use multiple options to mount more than one volume. "
    "--volume=HOME is an alias for storage://~:/var/storage/home:rw and "
    "storage://neuromation/public:/var/storage/neuromation:ro",
)
@click.option(
    "--entrypoint",
    type=str,
    help=(
        "Executable entrypoint in the container "
        "(note that it overwrites `ENTRYPOINT` and `CMD` "
        "instructions of the docker image)"
    ),
)
@click.option(
    "-e",
    "--env",
    metavar="VAR=VAL",
    multiple=True,
    help="Set environment variable in container "
    "Use multiple options to define more than one variable",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    help="File with environment variables to pass",
)
@click.option(
    "--wait-start/--no-wait-start",
    default=True,
    show_default=True,
    help="Wait for a job start or failure",
)
@click.option(
    "--pass-config/--no-pass-config",
    default=False,
    show_default=True,
    help="Upload neuro config to the job",
)
@click.option("--browse", is_flag=True, help="Open a job's URL in a web browser")
@click.option(
    "--detach",
    is_flag=True,
    help="Don't attach to job logs and don't wait for exit code",
)
@async_cmd()
async def submit(
    root: Root,
    image: RemoteImage,
    gpu: Optional[int],
    gpu_model: Optional[str],
    tpu_type: Optional[str],
    tpu_software_version: Optional[str],
    cpu: float,
    memory: int,
    extshm: bool,
    http: Optional[int],
    http_auth: Optional[bool],
    entrypoint: Optional[str],
    cmd: Sequence[str],
    volume: Sequence[str],
    env: Sequence[str],
    env_file: Optional[str],
    preemptible: bool,
    name: Optional[str],
    description: Optional[str],
    wait_start: bool,
    pass_config: bool,
    browse: bool,
    detach: bool,
) -> None:
    """
    Submit an image to run on the cluster.

    IMAGE container image name.

    CMD list will be passed as commands to model container.

    Examples:

    # Starts a container pytorch:latest with two paths mounted. Directory /q1/
    # is mounted in read only mode to /qm directory within container.
    # Directory /mod mounted to /mod directory in read-write mode.
    neuro submit --volume storage:/q1:/qm:ro --volume storage:/mod:/mod:rw \
      pytorch:latest

    # Starts a container using the custom image my-ubuntu:latest stored in neuromation
    # registry, run /script.sh and pass arg1 arg2 arg3 as its arguments:
    neuro submit image://~/my-ubuntu:latest --entrypoint=/script.sh arg1 arg2 arg3
    """
    await run_job(
        root,
        image=image,
        gpu=gpu,
        gpu_model=gpu_model,
        tpu_type=tpu_type,
        tpu_software_version=tpu_software_version,
        cpu=cpu,
        memory=memory,
        extshm=extshm,
        http=http,
        http_auth=http_auth,
        entrypoint=entrypoint,
        cmd=cmd,
        volume=volume,
        env=env,
        env_file=env_file,
        preemptible=preemptible,
        name=name,
        description=description,
        wait_start=wait_start,
        pass_config=pass_config,
        browse=browse,
        detach=detach,
    )


@command(context_settings=dict(allow_interspersed_args=False))
@click.argument("job")
@click.argument("cmd", nargs=-1, type=click.UNPROCESSED, required=True)
@click.option(
    "-t/-T",
    "--tty/--no-tty",
    default=True,
    is_flag=True,
    help="Allocate virtual tty. Useful for interactive jobs.",
)
@click.option(
    "--no-key-check",
    is_flag=True,
    help="Disable host key checks. Should be used with caution.",
)
@click.option(
    "--timeout",
    default=0,
    type=float,
    show_default=True,
    help="Maximum allowed time for executing the command, 0 for no timeout",
)
@async_cmd()
async def exec(
    root: Root,
    job: str,
    tty: bool,
    no_key_check: bool,
    cmd: Sequence[str],
    timeout: float,
) -> None:
    """
    Execute command in a running job.

    Examples:

    # Provides a shell to the container:
    neuro exec my-job /bin/bash

    # Executes a single command in the container and returns the control:
    neuro exec --no-tty my-job ls -l
    """
    cmd = shlex.split(" ".join(cmd))
    id = await resolve_job(job, client=root.client)
    retcode = await root.client.jobs.exec(
        id,
        cmd,
        tty=tty,
        no_key_check=no_key_check,
        timeout=timeout if timeout else None,
    )
    sys.exit(retcode)


@command()
@click.argument("job")
@click.argument("local_remote_port", type=LOCAL_REMOTE_PORT, nargs=-1, required=True)
@click.option(
    "--no-key-check",
    is_flag=True,
    help="Disable host key checks. Should be used with caution.",
)
@async_cmd()
async def port_forward(
    root: Root, job: str, no_key_check: bool, local_remote_port: List[Tuple[int, int]]
) -> None:
    """
    Forward port(s) of a running job to local port(s).

    Examples:

    # Forward local port 2080 to port 80 of job's container.
    # You can use http://localhost:2080 in browser to access job's served http
    neuro job port-forward my-fastai-job 2080:80

    # Forward local port 2222 to job's port 22
    # Then copy all data from container's folder '/data' to current folder
    # (please run second command in other terminal)
    neuro job port-forward my-job-with-ssh-server 2222:22
    rsync -avxzhe "ssh -p 2222" root@localhost:/data .

    # Forward few ports at once
    neuro job port-forward my-job- 2080:80 2222:22 2000:100

    """
    job_id = await resolve_job(job, client=root.client)
    async with AsyncExitStack() as stack:
        for local_port, job_port in local_remote_port:
            click.echo(
                f"Port localhost:{local_port} will be forwarded "
                f"to port {job_port} of {job_id}"
            )
            await stack.enter_async_context(
                root.client.jobs.port_forward(
                    job_id, local_port, job_port, no_key_check=no_key_check
                )
            )

        click.echo("Press ^C to stop forwarding")
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass


@command()
@click.argument("job")
@async_cmd()
async def logs(root: Root, job: str) -> None:
    """
    Print the logs for a container.
    """
    id = await resolve_job(job, client=root.client)
    await _print_logs(root, id)


async def _print_logs(root: Root, job: str) -> None:
    async for chunk in root.client.jobs.monitor(job):
        if not chunk:
            break
        click.echo(chunk.decode(errors="ignore"), nl=False)


@command()
@click.option(
    "-s",
    "--status",
    multiple=True,
    type=click.Choice(["pending", "running", "succeeded", "failed", "all"]),
    help=(
        "Filter out jobs by status (multiple option)."
        " Note: option `all` is deprecated, use `neuro ps -a` instead."
    ),
)
@click.option(
    "-o", "--owner", multiple=True, help="Filter out jobs by owner (multiple option)."
)
@click.option(
    "-a",
    "--all",
    is_flag=True,
    default=False,
    help=(
        "Show all jobs regardless the status (equivalent to "
        "`-s pending -s running -s succeeded -s failed`)"
    ),
)
@click.option("-n", "--name", metavar="NAME", help="Filter out jobs by name")
@click.option(
    "-d",
    "--description",
    metavar="DESCRIPTION",
    default="",
    help="Filter out jobs by description (exact match)",
)
@deprecated_quiet_option
@click.option(
    "-w", "--wide", is_flag=True, help="Do not cut long lines for terminal width"
)
@click.option(
    "--format", type=JOB_COLUMNS, help="Output table format", default=COLUMNS,
)
@async_cmd()
async def ls(
    root: Root,
    status: Sequence[str],
    all: bool,
    name: str,
    owner: Sequence[str],
    description: str,
    wide: bool,
    format: List[JobColumnInfo],
) -> None:
    """
    List all jobs.

    Examples:

    neuro ps -a
    neuro ps -a --owner=user-1 --owner=user-2
    neuro ps --name my-experiments-v1 -s failed -s succeeded
    neuro ps --description="my favourite job"
    neuro ps -s failed -s succeeded -q
    """

    statuses = calc_statuses(status, all)
    owners = set(owner)
    jobs = await root.client.jobs.list(statuses=statuses, name=name, owners=owners)

    # client-side filtering
    if description:
        jobs = [job for job in jobs if job.description == description]

    jobs.sort(key=lambda job: job.history.created_at)

    if root.quiet:
        formatter: BaseJobsFormatter = SimpleJobsFormatter()
    else:
        if wide or not root.tty:
            width = 0
        else:
            width = root.terminal_size[0]
        formatter = TabularJobsFormatter(width, root.client.username, format)

    pager_maybe(formatter(jobs), root.tty, root.terminal_size)


@command()
@click.argument("job")
@async_cmd()
async def status(root: Root, job: str) -> None:
    """
    Display status of a job.
    """
    id = await resolve_job(job, client=root.client)
    res = await root.client.jobs.status(id)
    click.echo(JobStatusFormatter()(res))


@command()
@click.argument("job")
@async_cmd()
async def browse(root: Root, job: str) -> None:
    """
    Opens a job's URL in a web browser.
    """
    id = await resolve_job(job, client=root.client)
    res = await root.client.jobs.status(id)
    await browse_job(root, res)


@command()
@click.argument("job")
@click.option(
    "--timeout",
    default=0,
    type=float,
    show_default=True,
    help="Maximum allowed time for executing the command, 0 for no timeout",
)
@async_cmd()
async def top(root: Root, job: str, timeout: float) -> None:
    """
    Display GPU/CPU/Memory usage.
    """
    formatter = JobTelemetryFormatter()
    id = await resolve_job(job, client=root.client)
    print_header = True
    async with async_timeout.timeout(timeout if timeout else None):
        async for res in root.client.jobs.top(id):
            if print_header:
                click.echo(formatter.header())
                print_header = False
            line = formatter(res)
            click.echo(f"\r{line}", nl=False)


@command()
@click.argument("job")
@click.argument("image", type=ImageType())
@async_cmd()
async def save(root: Root, job: str, image: RemoteImage) -> None:
    """
    Save job's state to an image.

    Examples:
    neuro job save job-id image:ubuntu-patched
    neuro job save my-favourite-job image://~/ubuntu-patched:v1
    neuro job save my-favourite-job image://bob/ubuntu-patched
    """
    id = await resolve_job(job, client=root.client)
    progress = DockerImageProgress.create(tty=root.tty, quiet=root.quiet)
    with contextlib.closing(progress):
        await root.client.jobs.save(id, image, progress=progress)
    click.echo(image)


@command()
@click.argument("jobs", nargs=-1, required=True)
@async_cmd()
async def kill(root: Root, jobs: Sequence[str]) -> None:
    """
    Kill job(s).
    """
    errors = []
    for job in jobs:
        job_resolved = await resolve_job(job, client=root.client)
        try:
            await root.client.jobs.kill(job_resolved)
            # TODO (ajuszkowski) printing should be on the cli level
            click.echo(job_resolved)
        except ValueError as e:
            errors.append((job, e))
        except AuthorizationError:
            errors.append((job, ValueError(f"Not enough permissions")))

    def format_fail(job: str, reason: Exception) -> str:
        return click.style(f"Cannot kill job {job}: {reason}", fg="red")

    for job, error in errors:
        click.echo(format_fail(job, error))


@command(context_settings=dict(allow_interspersed_args=False))
@click.argument("image", type=ImageType())
@click.argument("cmd", nargs=-1, type=click.UNPROCESSED)
@click.option(
    "-s",
    "--preset",
    metavar="PRESET",
    help=(
        "Predefined resource configuration (to see available values, "
        "run `neuro config show`)"
    ),
)
@click.option(
    "-x/-X",
    "--extshm/--no-extshm",
    is_flag=True,
    default=True,
    show_default=True,
    help="Request extended '/dev/shm' space",
)
@click.option(
    "--http",
    type=int,
    metavar="PORT",
    default=80,
    show_default=True,
    help="Enable HTTP port forwarding to container",
)
@click.option(
    "--http-auth/--no-http-auth",
    is_flag=True,
    help="Enable HTTP authentication for forwarded HTTP port  [default: True]",
    default=None,
)
@click.option(
    "--preemptible/--non-preemptible",
    "-p/-P",
    help="Run job on a lower-cost preemptible instance (DEPRECATED AND IGNORED)",
    default=None,
    hidden=True,
)
@click.option(
    "-n",
    "--name",
    metavar="NAME",
    type=JOB_NAME,
    help="Optional job name",
    default=None,
    show_default=True,
)
@click.option(
    "-d",
    "--description",
    metavar="DESC",
    help="Optional job description in free format",
)
@deprecated_quiet_option
@click.option(
    "-v",
    "--volume",
    metavar="MOUNT",
    multiple=True,
    help="Mounts directory from vault into container. "
    "Use multiple options to mount more than one volume. "
    "--volume=HOME is an alias for storage://~:/var/storage/home:rw and "
    "storage://neuromation/public:/var/storage/neuromation:ro",
)
@click.option(
    "--entrypoint",
    type=str,
    help=(
        "Executable entrypoint in the container "
        "(note that it overwrites `ENTRYPOINT` and `CMD` "
        "instructions of the docker image)"
    ),
)
@click.option(
    "-e",
    "--env",
    metavar="VAR=VAL",
    multiple=True,
    help="Set environment variable in container "
    "Use multiple options to define more than one variable",
)
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    help="File with environment variables to pass",
)
@click.option(
    "--wait-start/--no-wait-start",
    default=True,
    show_default=True,
    help="Wait for a job start or failure",
)
@click.option(
    "--pass-config/--no-pass-config",
    default=False,
    show_default=True,
    help="Upload neuro config to the job",
)
@click.option("--browse", is_flag=True, help="Open a job's URL in a web browser")
@click.option(
    "--detach",
    is_flag=True,
    help="Don't attach to job logs and don't wait for exit code",
)
@async_cmd()
async def run(
    root: Root,
    image: RemoteImage,
    preset: str,
    extshm: bool,
    http: int,
    http_auth: Optional[bool],
    entrypoint: Optional[str],
    cmd: Sequence[str],
    volume: Sequence[str],
    env: Sequence[str],
    env_file: Optional[str],
    preemptible: Optional[bool],
    name: Optional[str],
    description: Optional[str],
    wait_start: bool,
    pass_config: bool,
    browse: bool,
    detach: bool,
) -> None:
    """
    Run a job with predefined resources configuration.

    IMAGE container image name.

    CMD list will be passed as commands to model container.

    Examples:

    # Starts a container pytorch:latest on a machine with smaller GPU resources
    # (see exact values in `neuro config show`) and with two volumes mounted:
    #   storage://<home-directory>   --> /var/storage/home (in read-write mode),
    #   storage://neuromation/public --> /var/storage/neuromation (in read-only mode).
    neuro run --preset=gpu-small --volume=HOME pytorch:latest

    # Starts a container using the custom image my-ubuntu:latest stored in neuromation
    # registry, run /script.sh and pass arg1 and arg2 as its arguments:
    neuro run -s cpu-small image://~/my-ubuntu:latest --entrypoint=/script.sh arg1 arg2
    """
    if not preset:
        preset = next(iter(root.client.config.presets.keys()))
    job_preset = root.client.config.presets[preset]
    if preemptible is not None:
        click.echo(
            "-p/-P option is deprecated and ignored. Use corresponding presets instead."
        )
    log.info(f"Using preset '{preset}': {job_preset}")

    await run_job(
        root,
        image=image,
        gpu=job_preset.gpu,
        gpu_model=job_preset.gpu_model,
        tpu_type=job_preset.tpu_type,
        tpu_software_version=job_preset.tpu_software_version,
        cpu=job_preset.cpu,
        memory=job_preset.memory_mb,
        extshm=extshm,
        http=http,
        http_auth=http_auth,
        entrypoint=entrypoint,
        cmd=cmd,
        volume=volume,
        env=env,
        env_file=env_file,
        preemptible=job_preset.is_preemptible,
        name=name,
        description=description,
        wait_start=wait_start,
        pass_config=pass_config,
        browse=browse,
        detach=detach,
    )


job.add_command(run)
job.add_command(submit)
job.add_command(ls)
job.add_command(status)
job.add_command(exec)
job.add_command(port_forward)
job.add_command(logs)
job.add_command(kill)
job.add_command(top)
job.add_command(save)
job.add_command(browse)


job.add_command(alias(ls, "list", hidden=True))
job.add_command(alias(logs, "monitor", hidden=True))


async def run_job(
    root: Root,
    *,
    image: RemoteImage,
    gpu: Optional[int],
    gpu_model: Optional[str],
    tpu_type: Optional[str],
    tpu_software_version: Optional[str],
    cpu: float,
    memory: int,
    extshm: bool,
    http: Optional[int],
    http_auth: Optional[bool],
    entrypoint: Optional[str],
    cmd: Sequence[str],
    volume: Sequence[str],
    env: Sequence[str],
    env_file: Optional[str],
    preemptible: bool,
    name: Optional[str],
    description: Optional[str],
    wait_start: bool,
    pass_config: bool,
    browse: bool,
    detach: bool,
) -> JobDescription:
    if http_auth is None:
        http_auth = True
    elif not http:
        if http_auth:
            raise click.UsageError("--http-auth requires --http")
        else:
            raise click.UsageError("--no-http-auth requires --http")
    if browse and not http:
        raise click.UsageError("--browse requires --http")
    if browse and not wait_start:
        raise click.UsageError("Cannot use --browse and --no-wait-start together")
    if not wait_start:
        detach = True

    env_dict = build_env(env, env_file)

    if cmd is None:
        real_cmd: Optional[str] = None
    elif len(cmd) == 1:
        real_cmd = cmd[0]
    else:
        real_cmd = " ".join(shlex.quote(arg) for arg in cmd)

    log.debug(f'entrypoint="{entrypoint}"')
    log.debug(f'cmd="{cmd}"')

    log.info(f"Using image '{image}'")

    if tpu_type:
        if not tpu_software_version:
            raise ValueError(
                "--tpu-sw-version cannot be empty while --tpu-type specified"
            )
    resources = Resources(
        memory_mb=memory,
        cpu=cpu,
        gpu=gpu,
        gpu_model=gpu_model,
        shm=extshm,
        tpu_type=tpu_type,
        tpu_software_version=tpu_software_version,
    )
    volumes = await _build_volumes(root, volume, env_dict)

    if pass_config:
        if CONFIG_ENV_NAME in env_dict:
            raise ValueError(
                f"{CONFIG_ENV_NAME} is already set to {env_dict[CONFIG_ENV_NAME]}"
            )
        env_var, secret_volume = await upload_and_map_config(root)
        env_dict[CONFIG_ENV_NAME] = env_var
        env_dict[TRUSTED_CONFIG_PATH] = "1"
        volumes.add(secret_volume)

    if volumes:
        log.info(
            "Using volumes: \n"
            + "\n".join(f"  {volume_to_verbose_str(v)}" for v in volumes)
        )

    container = Container(
        image=image,
        entrypoint=entrypoint,
        command=real_cmd,
        http=HTTPPort(http, http_auth) if http else None,
        resources=resources,
        env=env_dict,
        volumes=list(volumes),
    )

    job = await root.client.jobs.run(
        container, is_preemptible=preemptible, name=name, description=description
    )
    click.echo(JobFormatter(root.quiet)(job))
    progress = JobStartProgress.create(tty=root.tty, color=root.color, quiet=root.quiet)
    while wait_start and job.status == JobStatus.PENDING:
        await asyncio.sleep(0.2)
        job = await root.client.jobs.status(job.id)
        progress(job)
    progress.close()
    if browse and job.status != JobStatus.FAILED:
        await browse_job(root, job)

    exit_code = None
    if not detach:
        if not root.quiet:
            msg = textwrap.dedent(
                """\
                Terminal is attached to the remote job, so you receive the job's output.
                Use 'Ctrl-C' to detach (it will NOT terminate the job), or restart the
                job with `--detach` option.\
                """
            )
            click.echo(click.style(msg, dim=True))
        await _print_logs(root, job.id)
        job = await root.client.jobs.status(job.id)
        exit_code = job.history.exit_code
    else:
        # Even if we detached, but the job has failed to start
        # (most common reason - no resources), the command fails
        if job.status == JobStatus.FAILED:
            exit_code = EX_PLATFORMERROR

    if exit_code is not None:
        sys.exit(exit_code)

    return job


async def _build_volumes(
    root: Root, input_volumes: Sequence[str], env_dict: Dict[str, str]
) -> Set[Volume]:
    input_volumes_set = set(input_volumes)
    volumes: Set[Volume] = set()

    if "ALL" in input_volumes_set:
        if len(input_volumes_set) > 1:
            raise click.UsageError(
                f"Cannot use `--volume=ALL` together with other `--volume` options"
            )
        available = await root.client.users.get_acl(
            root.client.username, scheme="storage"
        )
        permissions = []
        for perm in available:
            try:
                idna.encode(perm.uri.host)
            except ValueError:
                log.warning(f"Skipping invalid URI {perm.uri}")
            else:
                permissions.append(perm)
        volumes.update(
            Volume(
                storage_uri=perm.uri,
                container_path=f"{ROOT_MOUNTPOINT}/{perm.uri.host}{perm.uri.path}",
                read_only=perm.action not in ("write", "manage"),
            )
            for perm in permissions
        )
        neuro_mountpoint = _get_neuro_mountpoint(root.client.username)
        env_dict[NEUROMATION_HOME_ENV_VAR] = neuro_mountpoint
        env_dict[NEUROMATION_ROOT_ENV_VAR] = ROOT_MOUNTPOINT
        if not root.quiet:
            click.echo(
                "Storage mountpoints will be available as the environment variables:\n"
                f"  {NEUROMATION_ROOT_ENV_VAR}={ROOT_MOUNTPOINT}\n"
                f"  {NEUROMATION_HOME_ENV_VAR}={neuro_mountpoint}"
            )
    else:
        for vol in input_volumes_set:
            if vol == "HOME":
                volumes.add(
                    root.client.parse.volume(
                        f"storage://~:{STORAGE_MOUNTPOINT}/home:rw"
                    )
                )
                volumes.add(
                    root.client.parse.volume(
                        f"storage://neuromation/public:"
                        f"{STORAGE_MOUNTPOINT}/neuromation:ro"
                    )
                )
                click.echo(
                    click.style(
                        "DeprecationWarning: Option `--volume=HOME` is deprecated. "
                        "Use `--volume=ALL`.  Mountpoint will be available in "
                        "container via variable NEUROMATION_HOME",
                        fg="red",
                    ),
                    err=True,
                )
            else:
                volumes.add(root.client.parse.volume(vol))
    return volumes


async def upload_and_map_config(root: Root) -> Tuple[str, Volume]:

    # store the Neuro CLI config on the storage under some random path
    nmrc_path = URL(root.config_path.expanduser().resolve().as_uri())
    random_nmrc_filename = f"{uuid.uuid4()}-nmrc"
    storage_nmrc_folder = URL(f"storage://{root.client.username}/nmrc/")
    storage_nmrc_path = storage_nmrc_folder / random_nmrc_filename
    local_nmrc_folder = f"{STORAGE_MOUNTPOINT}/nmrc/"
    local_nmrc_path = f"{local_nmrc_folder}{random_nmrc_filename}"
    if not root.quiet:
        click.echo(f"Temporary config file created on storage: {storage_nmrc_path}.")
        click.echo(f"Inside container it will be available at: {local_nmrc_path}.")
    await root.client.storage.mkdir(storage_nmrc_folder, parents=True, exist_ok=True)
    await root.client.storage.upload_dir(nmrc_path, storage_nmrc_path)
    # specify a container volume and mount the storage path
    # into specific container path
    return (
        local_nmrc_path,
        Volume(
            storage_uri=storage_nmrc_folder,
            container_path=local_nmrc_folder,
            read_only=False,
        ),
    )


async def browse_job(root: Root, job: JobDescription) -> None:
    url = job.http_url
    if url.scheme not in ("http", "https"):
        raise RuntimeError(f"Cannot open job URL: {url}")
    log.info(f"Open job URL: {url}")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, webbrowser.open, str(url))


def calc_statuses(status: Sequence[str], all: bool) -> Set[JobStatus]:
    defaults = {"running", "pending"}
    statuses = set(status)

    if "all" in statuses:
        if all:
            raise click.UsageError(
                "Parameters `-a/--all` and " "`-s all/--status=all` are incompatible"
            )
        click.echo(
            click.style(
                "DeprecationWarning: "
                "Option `-s all/--status=all` is deprecated. "
                "Please use `-a/--all` instead.",
                fg="red",
            ),
            err=True,
        )
        statuses = set()
    else:
        if all:
            if statuses:
                opt = " ".join([f"--status={s}" for s in status])
                log.warning(f"Option `-a/--all` overwrites option(s) `{opt}`")
            statuses = set()
        elif not statuses:
            statuses = defaults

    return set(JobStatus(s) for s in statuses)
