import sys
from decimal import Decimal
from pathlib import Path
from typing import Callable
from unittest import mock

import pytest
from yarl import URL

from apolo_sdk import AppsConfig, Client, Cluster, Preset, Project, ResourcePool

from apolo_cli.config import prompt_cluster, prompt_project
from apolo_cli.root import Root
from apolo_cli.utils import Command, Context


async def cmd() -> None:
    pass


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Promt_toolkit fails in github actions worker",
)
def test_prompt_cluster(make_client: Callable[..., Client]) -> None:
    clusters = {
        "first": Cluster(
            registry_url=URL("https://registry-dev.neu.ro"),
            storage_url=URL("https://storage-dev.neu.ro"),
            users_url=URL("https://users-dev.neu.ro"),
            monitoring_url=URL("https://monitoring-dev.neu.ro"),
            secrets_url=URL("https://secrets-dev.neu.ro"),
            disks_url=URL("https://disks-dev.neu.ro"),
            buckets_url=URL("https://buckets-dev.neu.ro"),
            resource_pools={
                "cpu": ResourcePool(
                    min_size=1,
                    max_size=2,
                    cpu=7,
                    memory=14 * 2**30,
                    disk_size=150 * 2**30,
                ),
            },
            presets={
                "cpu-small": Preset(credits_per_hour=Decimal("10"), cpu=1, memory=2**30)
            },
            name="first",
            orgs=["NO_ORG"],
            apps=AppsConfig(),
        ),
        "second": Cluster(
            registry_url=URL("https://registry2-dev.neu.ro"),
            storage_url=URL("https://storage2-dev.neu.ro"),
            users_url=URL("https://users2-dev.neu.ro"),
            monitoring_url=URL("https://monitoring2-dev.neu.ro"),
            secrets_url=URL("https://secrets2-dev.neu.ro"),
            disks_url=URL("https://disks2-dev.neu.ro"),
            buckets_url=URL("https://buckets2-dev.neu.ro"),
            resource_pools={
                "cpu": ResourcePool(
                    min_size=1,
                    max_size=2,
                    cpu=7,
                    memory=14 * 2**30,
                    disk_size=150 * 2**30,
                ),
            },
            presets={
                "cpu-small": Preset(credits_per_hour=Decimal("10"), cpu=2, memory=2**30)
            },
            name="second",
            orgs=["NO_ORG"],
            apps=AppsConfig(),
        ),
    }

    root = Root(
        color=False,
        tty=False,
        disable_pypi_version_check=True,
        network_timeout=60,
        config_path=Path("<config-path>"),
        verbosity=0,
        trace=False,
        trace_hide_token=True,
        force_trace_all=False,
        command_path="",
        command_params=[],
        skip_gmp_stats=True,
        show_traceback=False,
        iso_datetime_format=False,
        ctx=Context(Command(cmd, name="")),
    )

    async def _async_make_client() -> Client:
        return make_client("https://neu.ro", clusters=clusters)

    root._client = root.run(_async_make_client())

    session = mock.Mock()
    loop = root._runner._loop
    assert loop is not None
    fut = loop.create_future()
    fut.set_result("second")
    session.prompt_async.return_value = fut
    ret = root.run(prompt_cluster(root, session=session))
    assert ret == "second"
    root.close()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Promt_toolkit fails in github actions worker",
)
def test_prompt_cluster_default(make_client: Callable[..., Client]) -> None:
    clusters = {
        "first": Cluster(
            registry_url=URL("https://registry-dev.neu.ro"),
            storage_url=URL("https://storage-dev.neu.ro"),
            users_url=URL("https://users-dev.neu.ro"),
            monitoring_url=URL("https://monitoring-dev.neu.ro"),
            secrets_url=URL("https://secrets-dev.neu.ro"),
            disks_url=URL("https://disks-dev.neu.ro"),
            buckets_url=URL("https://buckets-dev.neu.ro"),
            resource_pools={
                "cpu": ResourcePool(
                    min_size=1,
                    max_size=2,
                    cpu=7,
                    memory=14 * 2**30,
                    disk_size=150 * 2**30,
                ),
            },
            presets={
                "cpu-small": Preset(credits_per_hour=Decimal("10"), cpu=1, memory=2**30)
            },
            name="first",
            orgs=["NO_ORG"],
            apps=AppsConfig(),
        ),
        "second": Cluster(
            registry_url=URL("https://registry2-dev.neu.ro"),
            storage_url=URL("https://storage2-dev.neu.ro"),
            users_url=URL("https://users2-dev.neu.ro"),
            monitoring_url=URL("https://monitoring2-dev.neu.ro"),
            secrets_url=URL("https://secrets2-dev.neu.ro"),
            disks_url=URL("https://disks2-dev.neu.ro"),
            buckets_url=URL("https://disks2-dev.neu.ro"),
            resource_pools={
                "cpu": ResourcePool(
                    min_size=1,
                    max_size=2,
                    cpu=7,
                    memory=14 * 2**30,
                    disk_size=150 * 2**30,
                ),
            },
            presets={
                "cpu-small": Preset(credits_per_hour=Decimal("10"), cpu=2, memory=2**30)
            },
            name="second",
            orgs=["NO_ORG"],
            apps=AppsConfig(),
        ),
    }

    root = Root(
        color=False,
        tty=False,
        disable_pypi_version_check=True,
        network_timeout=60,
        config_path=Path("<config-path>"),
        verbosity=0,
        trace=False,
        trace_hide_token=True,
        force_trace_all=False,
        command_path="",
        command_params=[],
        skip_gmp_stats=True,
        show_traceback=False,
        iso_datetime_format=False,
        ctx=Context(Command(cmd, name="")),
    )

    async def _async_make_client() -> Client:
        return make_client("https://neu.ro", clusters=clusters)

    root._client = root.run(_async_make_client())

    session = mock.Mock()
    loop = root._runner._loop
    assert loop is not None
    fut = loop.create_future()
    fut.set_result("")
    session.prompt_async.return_value = fut

    ret = root.run(prompt_cluster(root, session=session))
    assert ret == "first"
    root.close()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Prompt_toolkit fails in github actions worker",
)
def test_prompt_project(make_client: Callable[..., Client]) -> None:
    clusters = {
        "default": Cluster(
            name="default",
            registry_url=URL("https://registry-dev.neu.ro"),
            storage_url=URL("https://storage-dev.neu.ro"),
            users_url=URL("https://users-dev.neu.ro"),
            monitoring_url=URL("https://monitoring-dev.neu.ro"),
            secrets_url=URL("https://secrets-dev.neu.ro"),
            disks_url=URL("https://disks-dev.neu.ro"),
            buckets_url=URL("https://buckets-dev.neu.ro"),
            resource_pools={
                "cpu": ResourcePool(
                    min_size=1,
                    max_size=2,
                    cpu=7,
                    memory=14 * 2**30,
                    disk_size=150 * 2**30,
                ),
            },
            presets={
                "cpu-small": Preset(credits_per_hour=Decimal("10"), cpu=1, memory=2**30)
            },
            orgs=["NO_ORG"],
            apps=AppsConfig(),
        ),
    }
    project = Project(
        name="main", cluster_name="default", org_name="NO_ORG", role="owner"
    )
    projects = {project.key: project}

    root = Root(
        color=False,
        tty=False,
        disable_pypi_version_check=True,
        network_timeout=60,
        config_path=Path("<config-path>"),
        verbosity=0,
        trace=False,
        trace_hide_token=True,
        force_trace_all=False,
        command_path="",
        command_params=[],
        skip_gmp_stats=True,
        show_traceback=False,
        iso_datetime_format=False,
        ctx=Context(Command(cmd, name="")),
    )

    async def _async_make_client() -> Client:
        return make_client("https://neu.ro", clusters=clusters, projects=projects)

    root._client = root.run(_async_make_client())

    session = mock.Mock()
    loop = root._runner._loop
    assert loop is not None
    fut = loop.create_future()
    fut.set_result("main")
    session.prompt_async.return_value = fut
    ret = root.run(prompt_project(root, session=session))
    assert ret == "main"
    root.close()


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Prompt_toolkit fails in github actions worker",
)
def test_prompt_project_default(make_client: Callable[..., Client]) -> None:
    clusters = {
        "default": Cluster(
            name="default",
            registry_url=URL("https://registry-dev.neu.ro"),
            storage_url=URL("https://storage-dev.neu.ro"),
            users_url=URL("https://users-dev.neu.ro"),
            monitoring_url=URL("https://monitoring-dev.neu.ro"),
            secrets_url=URL("https://secrets-dev.neu.ro"),
            disks_url=URL("https://disks-dev.neu.ro"),
            buckets_url=URL("https://buckets-dev.neu.ro"),
            resource_pools={
                "cpu": ResourcePool(
                    min_size=1,
                    max_size=2,
                    cpu=7,
                    memory=14 * 2**30,
                    disk_size=150 * 2**30,
                ),
            },
            presets={
                "cpu-small": Preset(credits_per_hour=Decimal("10"), cpu=1, memory=2**30)
            },
            orgs=["NO_ORG"],
            apps=AppsConfig(),
        ),
    }
    project = Project(
        name="main", cluster_name="default", org_name="NO_ORG", role="owner"
    )
    projects = {project.key: project}

    root = Root(
        color=False,
        tty=False,
        disable_pypi_version_check=True,
        network_timeout=60,
        config_path=Path("<config-path>"),
        verbosity=0,
        trace=False,
        trace_hide_token=True,
        force_trace_all=False,
        command_path="",
        command_params=[],
        skip_gmp_stats=True,
        show_traceback=False,
        iso_datetime_format=False,
        ctx=Context(Command(cmd, name="")),
    )

    async def _async_make_client() -> Client:
        return make_client(
            "https://neu.ro",
            clusters=clusters,
            projects=projects,
            project_name=project.name,
        )

    root._client = root.run(_async_make_client())

    session = mock.Mock()
    loop = root._runner._loop
    assert loop is not None
    fut = loop.create_future()
    fut.set_result("")
    session.prompt_async.return_value = fut
    ret = root.run(prompt_project(root, session=session))
    assert ret == "main"
    root.close()
