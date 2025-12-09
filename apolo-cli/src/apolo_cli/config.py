import asyncio
import contextvars
import json
import os
import sys
import webbrowser
from pathlib import Path
from typing import Any

import click
from aiohttp.client_exceptions import ClientConnectionError
from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
from rich.markup import escape as rich_escape
from yarl import URL

from apolo_sdk import DEFAULT_API_URL, AuthorizationError, ConfigError

from apolo_cli.formatters.config import ClustersFormatter

from .alias import list_aliases
from .click_types import CLUSTER_ALLOW_UNKNOWN, ORG, PROJECT_ALLOW_UNKNOWN
from .formatters.config import (
    AliasesFormatter,
    ClusterOrgProjectsFormatter,
    ConfigFormatter,
)
from .root import Root
from .utils import argument, command, group, option

ROOT: contextvars.ContextVar[Root] = contextvars.ContextVar("ROOT")


@group()
def config() -> None:
    """Client configuration."""


@command()
@option(
    "--energy",
    is_flag=True,
    help="Including cluster energy consumption and CO2 emissions information",
)
async def show(root: Root, energy: bool) -> None:
    """
    Print current settings.
    """

    with root.status("Fetching the current config"):
        await root.client.config.fetch()
    cluster_name = root.client.config.cluster_name
    fmt = ConfigFormatter()
    with root.status("Fetching the jobs capacity"):
        try:
            jobs_capacity = await root.client.jobs.get_capacity(
                cluster_name=cluster_name
            )
        except (ClientConnectionError, AuthorizationError):
            jobs_capacity = {}
    with root.status("Fetching user job quota"):
        quota = await root.client.users.get_quota()
        org_quota = await root.client.users.get_org_quota()
    config_cluster = None
    if energy:
        with root.status("Fetching cluster energy schedules"):
            config_cluster = await root.client._clusters.get_cluster(cluster_name)
    root.print(fmt(root.client.config, jobs_capacity, quota, org_quota, config_cluster))


@command()
async def show_token(root: Root) -> None:
    """
    Print current authorization token.
    """
    root.print(await root.client.config.token(), soft_wrap=True)


def _print_welcome(root: Root, url: URL) -> None:
    if root.client.config.clusters:
        root.print(
            f"Logged into {url} as [u]{root.client.config.username}[/u]"
            f", current cluster is [b]{root.client.config.cluster_name}[/b], "
            f"org is [b]{root.client.config.org_name}[/b]",
            f"project is [b]{root.client.config.project_name}[/b]",
            markup=True,
        )
    else:
        root.print(
            f"Logged into {url} as [u]{root.client.config.username}[/u]", markup=True
        )
    root.print(
        "Read the docs at https://docs.apolo.us or run `apolo --help` "
        "to see the reference"
    )


async def _show_browser(url: URL) -> None:
    loop = asyncio.get_event_loop()
    root = ROOT.get()
    success = await loop.run_in_executor(None, webbrowser.open_new, str(url))
    if not success:
        raise Exception(
            "No browser found. For non-GUI environments, use "
            "`apolo config login-headless` to login."
        )
    else:
        root.print(
            f"[dim]Your browser has been opened to visit:[/dim] [b]{url}[/b]",
            markup=True,
        )


@command(init_client=False)
@argument("url", required=False, default=DEFAULT_API_URL, type=URL)
async def login(root: Root, url: URL) -> None:
    """
    Log into Apolo Platform.

    URL is a platform entrypoint URL.
    """

    token = ROOT.set(root)
    try:
        await root.factory.login(_show_browser, url=url, timeout=root.timeout)
    except (ConfigError, FileExistsError):
        await root.factory.logout()
        root.print("You were successfully logged out.")
        await root.factory.login(_show_browser, url=url, timeout=root.timeout)
    finally:
        ROOT.reset(token)
    await root.init_client()
    _print_welcome(root, url)


@command(init_client=False)
@argument("token", required=True, type=str)
@argument("url", required=False, default=DEFAULT_API_URL, type=URL)
async def login_with_token(root: Root, token: str, url: URL) -> None:
    """
    Log into Apolo Platform with token.

    TOKEN is authentication token provided by administration team.
    URL is a platform entrypoint URL.
    """
    try:
        await root.factory.login_with_token(token, url=url, timeout=root.timeout)
    except ConfigError:
        await root.factory.logout()
        root.print("You were successfully logged out.")
        await root.factory.login_with_token(token, url=url, timeout=root.timeout)
    await root.init_client()
    _print_welcome(root, url)


@command(init_client=False)
@argument("url", required=False, default=DEFAULT_API_URL, type=URL)
async def login_headless(root: Root, url: URL) -> None:
    """
    Log into Apolo Platform in non-GUI environ

    URL is a platform entrypoint URL.

    The command works similar to "apolo login" but instead of
    opening a browser for performing OAuth registration prints
    an URL that should be open on guest host.

    Then user inputs a code displayed in a browser after successful login
    back in apolo command to finish the login process.
    """

    async def login_callback(url: URL) -> str:
        session: PromptSession[str] = PromptSession()
        root.print(f"Open {url} in a browser")
        root.print("Put the code displayed in a browser after successful login")
        with patch_stdout():
            auth_code = await session.prompt_async("Code (empty for exit)-> ")
        if not auth_code:
            sys.exit()
        return auth_code

    try:
        await root.factory.login_headless(login_callback, url=url, timeout=root.timeout)
    except ConfigError:
        await root.factory.logout()
        root.print("You were successfully logged out.")
        await root.factory.login_headless(login_callback, url=url, timeout=root.timeout)
    await root.init_client()
    _print_welcome(root, url)


@command(init_client=False)
async def logout(root: Root) -> None:
    """
    Log out.
    """
    token = ROOT.set(root)
    try:
        await root.factory.logout(_show_browser)
    finally:
        ROOT.reset(token)
    root.print("Logged out")


@command(init_client=False)
async def aliases(root: Root) -> None:
    """
    List available command aliases.
    """
    aliases = await list_aliases(root)
    root.print(AliasesFormatter()(aliases))


@command(name="docker")
@option(
    "--docker-config",
    metavar="PATH",
    type=click.Path(file_okay=False),
    help="Specifies the location of the Docker client configuration files",
    default=lambda: os.environ.get("DOCKER_CONFIG", Path.home() / ".docker"),
    show_default=False,
)
async def docker(root: Root, docker_config: str) -> None:
    """
    Configure local docker client

    This command configures local docker client to
    use Apolo Platform's docker registry.
    """
    config_path = Path(docker_config)
    if not config_path.exists():
        config_path.mkdir(parents=True)
    elif not config_path.is_dir():
        raise ValueError(f"Specified path is not a directory: {config}")

    json_path = config_path / "config.json"
    payload: dict[str, Any] = {}
    if json_path.exists():
        with json_path.open("rb") as file:
            payload = json.load(file)
    if "credHelpers" not in payload:
        payload["credHelpers"] = {}

    registry = URL(root.client.config.registry_url).host or ""
    payload["credHelpers"][registry] = "apolo"
    with json_path.open("w", encoding="utf-8") as file2:
        json.dump(payload, file2, indent=2)

    root.print(f"Configuration file {json_path} updated.")
    root.print(
        f"You can use docker client with apolo registry: "
        f"[b]{rich_escape(registry)}[/b]",
        markup=True,
    )


@command()
async def get_clusters(root: Root) -> None:
    """
    List available clusters/org pairs.

    This command re-fetches cluster list and then displays each
    cluster with available orgs.
    """

    with root.status("Fetching the list of available clusters"):
        await root.client.config.fetch()
    fmt = ClustersFormatter()
    with root.pager():
        root.print(
            fmt(
                root.client.config.clusters.values(),
                root.client.config.cluster_name,
                root.client.config.org_name,
            )
        )


@command()
@argument("cluster_name", required=False, default=None, type=CLUSTER_ALLOW_UNKNOWN)
async def switch_cluster(root: Root, cluster_name: str | None) -> None:
    """
    Switch the active cluster.

    CLUSTER_NAME is the cluster name to select.  The interactive prompt is used if the
    name is omitted (default).

    """
    with root.status("Fetching the list of available clusters"):
        await root.client.config.fetch()
    if cluster_name is None:
        if not root.tty:
            raise click.BadArgumentUsage(
                "Interactive mode is disabled for non-TTY mode, "
                "please specify the CLUSTER_NAME"
            )
        real_cluster_name = await prompt_cluster(root)
    else:
        real_cluster_name = cluster_name
    await root.client.config.switch_cluster(real_cluster_name)
    root.print(
        f"The current cluster is [u]{rich_escape(real_cluster_name)}[/u]", markup=True
    )


@command()
@argument("org_name", required=True, type=ORG)
async def switch_org(root: Root, org_name: str) -> None:
    """
    Switch the active organization.

    ORG_NAME is the organization name to select.
    """
    with root.status("Fetching the list of available cluster/org pairs"):
        await root.client.config.fetch()
    await root.client.config.switch_org(org_name)
    root.print(
        f"The current org_name is [u]{rich_escape(org_name or '<no-org>')}[/u]",
        markup=True,
    )


@command()
@argument("project_name", required=False, default=None, type=PROJECT_ALLOW_UNKNOWN)
async def switch_project(root: Root, project_name: str | None) -> None:
    """
    Switch the active project.

    PROJECT_NAME is the project name to select. The interactive prompt is used if the
    name is omitted (default).

    """
    with root.status("Fetching the list of available projects"):
        await root.client.config.fetch()
    if project_name is None:
        if not root.tty:
            raise click.BadArgumentUsage(
                "Interactive mode is disabled for non-TTY mode, "
                "please specify the PROJECT_NAME"
            )
        real_project_name = await prompt_project(root)
    else:
        real_project_name = project_name
    await root.client.config.switch_project(real_project_name)
    root.print(
        f"The current project is [u]{rich_escape(real_project_name)}[/u]", markup=True
    )


async def prompt_cluster(
    root: Root, *, session: PromptSession[str] | None = None
) -> str:
    if session is None:
        session = PromptSession()
    clusters = root.client.config.clusters
    while True:
        fmt = ClustersFormatter()
        root.print(
            fmt(
                clusters.values(),
                root.client.config.cluster_name,
                root.client.config.org_name,
            )
        )
        with patch_stdout():
            answer = await session.prompt_async(
                f"Select cluster to switch [{root.client.config.cluster_name}]: "
            )
        answer = answer.strip()
        if not answer:
            answer = root.client.config.cluster_name
        if answer not in clusters:
            root.print(
                f"Selected cluster [u]{rich_escape(answer)}[/u] "
                f"doesn't exist, please try again.",
                markup=True,
            )
        else:
            return answer


async def prompt_project(
    root: Root, *, session: PromptSession[str] | None = None
) -> str:
    if session is None:
        session = PromptSession()
    projects = sorted(p.name for p in root.client.config.cluster_org_projects)
    while True:
        fmt = ClusterOrgProjectsFormatter()
        root.print(fmt(projects, root.client.config.project_name))
        with patch_stdout():
            answer = await session.prompt_async(
                f"Select project to switch [{root.client.config.project_name}]: "
            )
        answer = answer.strip()
        if not answer:
            if not root.client.config.project_name:
                continue
            answer = root.client.config.project_name
        if answer not in projects:
            root.print(
                f"Selected project [u]{rich_escape(answer)}[/u] "
                f"doesn't exist, please try again.",
                markup=True,
            )
        else:
            return answer


config.add_command(login)
config.add_command(login_with_token)
config.add_command(login_headless)
config.add_command(show)
config.add_command(show_token)
config.add_command(aliases)
config.add_command(get_clusters)
config.add_command(switch_project)
config.add_command(switch_cluster)
config.add_command(switch_org)

config.add_command(docker)

config.add_command(logout)
