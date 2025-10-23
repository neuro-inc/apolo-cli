import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, Tuple

import pytest
import toml
from dateutil.parser import isoparse
from yarl import URL

from apolo_sdk import (
    Client,
    Container,
    DiskVolume,
    JobDescription,
    JobPriority,
    JobRestartPolicy,
    JobStatus,
    JobStatusHistory,
    PluginManager,
    RemoteImage,
    Resources,
    SecretFile,
    Volume,
)

from apolo_cli.job import (
    _job_to_cli_args,
    _parse_cmd,
    calc_ps_columns,
    calc_statuses,
    calc_top_columns,
)
from apolo_cli.parse_utils import (
    PS_COLUMNS_MAP,
    TOP_COLUMNS_MAP,
    get_default_ps_columns,
    get_default_top_columns,
)
from apolo_cli.root import Root

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_MakeClient = Callable[..., Client]


@pytest.mark.parametrize("statuses", [("all",), ("all", "failed", "succeeded")])
def test_calc_statuses__contains_all(statuses: Tuple[str]) -> None:
    with pytest.raises(
        ValueError,
        match="'all' is not a valid JobStatus",
    ):
        calc_statuses(statuses, all=False)


def test_calc_statuses__all_statuses_true(capsys: Any, caplog: Any) -> None:
    assert calc_statuses(["succeeded", "pending"], all=True) == set()
    std = capsys.readouterr()
    assert not std.out
    assert not std.err
    warning = (
        "Option `-a/--all` overwrites option(s) "
        "`--status=succeeded --status=pending`"
    )
    assert warning in caplog.text


def test_calc_statuses__all_statuses_true__quiet_mode(capsys: Any, caplog: Any) -> None:
    caplog.set_level(logging.ERROR)

    assert calc_statuses(["succeeded", "pending"], all=True) == set()
    std = capsys.readouterr()
    assert not std.out
    assert not std.err
    assert not caplog.text


def test_calc_statuses__all_statuses_false(capsys: Any, caplog: Any) -> None:
    assert calc_statuses(["succeeded", "pending"], all=False) == {
        JobStatus.SUCCEEDED,
        JobStatus.PENDING,
    }
    std = capsys.readouterr()
    assert not std.out
    assert not std.err
    assert not caplog.text


def test_calc_statuses__check_defaults__all_statuses_false(
    capsys: Any, caplog: Any
) -> None:
    assert calc_statuses([], all=False) == {
        JobStatus.PENDING,
        JobStatus.RUNNING,
        JobStatus.SUSPENDED,
    }
    std = capsys.readouterr()
    assert not std.out
    assert not std.err
    assert not caplog.text


def test_calc_statuses__check_defaults__all_statuses_true(
    capsys: Any, caplog: Any
) -> None:
    assert calc_statuses([], all=True) == set()
    std = capsys.readouterr()
    assert not std.out
    assert not std.err
    assert not caplog.text


def test_build_env_blank_lines(tmp_path: Path, root: Root) -> None:
    env_file = tmp_path / "env_var.txt"
    env_file.write_text("ENV_VAR_1=value1\n\n  \n\t\nENV_VAR_2=value2")
    assert root.client.parse._build_env([], [str(env_file)]) == {
        "ENV_VAR_1": "value1",
        "ENV_VAR_2": "value2",
    }


def test_build_env_comments(tmp_path: Path, root: Root) -> None:
    env_file = tmp_path / "env_var.txt"
    env_file.write_text("ENV_VAR_1=value1\n#ENV_VAR_2=value2\nENV_VAR_3=#value3#")
    assert root.client.parse._build_env([], [str(env_file)]) == {
        "ENV_VAR_1": "value1",
        "ENV_VAR_3": "#value3#",
    }


def test_build_env_multiple_files(tmp_path: Path, root: Root) -> None:
    env_1 = ("ENV_VAR_1=value1",)
    env_2 = ("ENV_VAR_2=value2",)
    env_file1 = tmp_path / "env_var.txt"
    env_file1.write_text("\n".join(env_1))
    env_file2 = tmp_path / "env_var2.txt"
    env_file2.write_text("\n".join(env_2))

    assert root.client.parse._build_env([], [str(env_file1), str(env_file2)]) == {
        "ENV_VAR_1": "value1",
        "ENV_VAR_2": "value2",
    }


def test_build_env_override_literals(root: Root) -> None:
    env = ("ENV_VAR=value1", "ENV_VAR=value2")

    assert root.client.parse._build_env(env) == {
        "ENV_VAR": "value2",
    }


def test_build_env_override_literal_and_file(tmp_path: Path, root: Root) -> None:
    env_1 = ("ENV_VAR=value1",)
    env_2 = ("ENV_VAR=value2",)
    env_file = tmp_path / "env_var.txt"
    env_file.write_text("\n".join(env_2))

    assert root.client.parse._build_env(env_1, [str(env_file)]) == {
        "ENV_VAR": "value1",
    }


def test_build_env_override_same_file(tmp_path: Path, root: Root) -> None:
    env = (
        "ENV_VAR=value1",
        "ENV_VAR=value2",
    )
    env_file = tmp_path / "env_var.txt"
    env_file.write_text("\n".join(env))

    assert root.client.parse._build_env([], [str(env_file)]) == {
        "ENV_VAR": "value2",
    }


def test_build_env_override_different_files(tmp_path: Path, root: Root) -> None:
    env_1 = ("ENV_VAR=value1",)
    env_2 = ("ENV_VAR=value2",)
    env_file1 = tmp_path / "env_var.txt"
    env_file1.write_text("\n".join(env_1))
    env_file2 = tmp_path / "env_var2.txt"
    env_file2.write_text("\n".join(env_2))

    assert root.client.parse._build_env([], [str(env_file1), str(env_file2)]) == {
        "ENV_VAR": "value2",
    }


def test_extract_secret_env(root: Root) -> None:
    project_name = root.client.config.project_name
    cluster_name = root.client.cluster_name
    env = {
        "ENV_VAR_1": "secret:value1",
        "ENV_VAR_2": "value2",
        "ENV_VAR_3": "secret:/otherproject/value3",
        "ENV_VAR_4": "value4",
        "ENV_VAR_5": "secret://othercluster/otherproject/value5",
    }
    assert root.client.parse._extract_secret_env(env) == {
        "ENV_VAR_1": URL(f"secret://{cluster_name}/org/{project_name}/value1"),
        "ENV_VAR_3": URL(f"secret://{cluster_name}/org/otherproject/value3"),
        "ENV_VAR_5": URL(f"secret://othercluster/otherproject/value5"),
    }
    assert env == {"ENV_VAR_2": "value2", "ENV_VAR_4": "value4"}


async def test_calc_ps_columns_section_doesnt_exist(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    async with make_client("https://example.com") as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        # empty config
        local_conf.write_text("")
        assert await calc_ps_columns(client, None) == get_default_ps_columns()


async def test_calc_top_columns_section_doesnt_exist(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    async with make_client("https://example.com") as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        # empty config
        local_conf.write_text("")
        assert await calc_top_columns(client, None) == get_default_top_columns()


async def test_calc_ps_columns_user_spec(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "ps-format")

    async with make_client(
        "https://example.com",
        plugin_manager=plugin_manager,
    ) as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        # empty config
        local_conf.write_text(toml.dumps({"job": {"ps-format": "{id}, {status}"}}))
        assert await calc_ps_columns(client, None) == [
            PS_COLUMNS_MAP["id"],
            PS_COLUMNS_MAP["status"],
        ]


async def test_calc_top_columns_user_spec(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str("job", "top-format")

    async with make_client(
        "https://example.com", plugin_manager=plugin_manager
    ) as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        # empty config
        local_conf.write_text(toml.dumps({"job": {"top-format": "{id}, {cpu}"}}))
        assert await calc_top_columns(client, None) == [
            TOP_COLUMNS_MAP["id"],
            TOP_COLUMNS_MAP["cpu"],
        ]


def test_parse_cmd_single() -> None:
    cmd = ["bash -c 'ls -l && pwd'"]
    assert _parse_cmd(cmd) == "bash -c 'ls -l && pwd'"


def test_parse_cmd_multiple() -> None:
    cmd = ["bash", "-c", "ls -l && pwd"]
    assert _parse_cmd(cmd) == "bash -c 'ls -l && pwd'"


def test_job_to_args_simple() -> None:
    job = JobDescription(
        status=JobStatus.FAILED,
        owner="test-user",
        project_name="myproj",
        cluster_name="default",
        org_name="my_org",
        namespace="",
        id=f"job",
        uri=URL(f"job://default/test-user/job"),
        description=None,
        history=JobStatusHistory(
            status=JobStatus.FAILED,
            reason="ErrorReason",
            description="ErrorDesc",
            created_at=isoparse("2018-09-25T12:28:21.298672+00:00"),
            started_at=isoparse("2018-09-25T12:28:59.759433+00:00"),
            finished_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        ),
        container=Container(
            command="test-command",
            image=RemoteImage.new_external_image(name="test-image"),
            resources=Resources(memory=16, cpu=0.1, shm=True),
        ),
        scheduler_enabled=False,
        pass_config=False,
        preset_name="testing",
        total_price_credits=Decimal("150"),
        price_credits_per_hour=Decimal("15"),
    )
    assert _job_to_cli_args(job) == [
        "--preset",
        "testing",
        "--project",
        "myproj",
        "test-image",
        "--",
        "test-command",
    ]


def test_job_to_args_drop_env_when_pass_config() -> None:
    job = JobDescription(
        status=JobStatus.FAILED,
        owner="test-user",
        project_name="myproj",
        cluster_name="default",
        org_name="my_org",
        namespace="",
        id=f"job",
        uri=URL(f"job://default/test-user/job"),
        description=None,
        history=JobStatusHistory(
            status=JobStatus.FAILED,
            reason="ErrorReason",
            description="ErrorDesc",
            created_at=isoparse("2018-09-25T12:28:21.298672+00:00"),
            started_at=isoparse("2018-09-25T12:28:59.759433+00:00"),
            finished_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        ),
        container=Container(
            command="test-command",
            image=RemoteImage.new_external_image(name="test-image"),
            resources=Resources(memory=16, cpu=0.1, shm=True),
            env={
                "APOLO_PASSED_CONFIG": "base64 data here",
            },
        ),
        scheduler_enabled=False,
        pass_config=True,
        preset_name="testing",
        total_price_credits=Decimal("150"),
        price_credits_per_hour=Decimal("15"),
    )
    assert _job_to_cli_args(job) == [
        "--preset",
        "testing",
        "--pass-config",
        "--project",
        "myproj",
        "test-image",
        "--",
        "test-command",
    ]


def test_job_to_args_complex() -> None:
    job = JobDescription(
        status=JobStatus.FAILED,
        owner="test-user",
        name="test-job",
        tags=["tag-1", "tag-2"],
        project_name="myproject",
        cluster_name="default",
        org_name="my_org",
        namespace="",
        id=f"job",
        uri=URL(f"job://default/test-user/job"),
        description="test description",
        restart_policy=JobRestartPolicy.ALWAYS,
        history=JobStatusHistory(
            status=JobStatus.FAILED,
            reason="ErrorReason",
            description="ErrorDesc",
            created_at=isoparse("2018-09-25T12:28:21.298672+00:00"),
            started_at=isoparse("2018-09-25T12:28:59.759433+00:00"),
            finished_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        ),
        container=Container(
            command="test-command",
            image=RemoteImage.new_external_image(name="test-image"),
            resources=Resources(memory=16, cpu=0.1, shm=False),
            working_dir="/mnt/test",
            volumes=[
                Volume(
                    storage_uri=URL("storage://test-cluster/test-user/_ro_"),
                    container_path="/mnt/_ro_",
                    read_only=True,
                ),
                Volume(
                    storage_uri=URL("storage://test-cluster/test-user/rw"),
                    container_path="/mnt/rw",
                    read_only=False,
                ),
            ],
            secret_files=[
                SecretFile(
                    URL("secret://test-cluster/test-user/secret1"),
                    "/var/run/secret1",
                ),
                SecretFile(
                    URL("secret://test-cluster/otheruser/secret2"),
                    "/var/run/secret2",
                ),
            ],
            disk_volumes=[
                DiskVolume(
                    URL("disk://test-cluster/test-user/disk1"),
                    "/mnt/disk1",
                    read_only=True,
                ),
                DiskVolume(
                    URL("disk://test-cluster/otheruser/disk2"),
                    "/mnt/disk2",
                    read_only=False,
                ),
            ],
            secret_env={
                "ENV_NAME_1": URL("secret://test-cluster/test-user/secret4"),
                "ENV_NAME_2": URL("secret://test-cluster/otheruser/secret5"),
            },
            env={
                "ENV_NAME_3": "TEST1",
                "ENV_NAME_4": "TEST2",
            },
        ),
        scheduler_enabled=True,
        pass_config=True,
        preset_name="testing",
        life_span=200,
        schedule_timeout=3600 * 24 * 2 + 3600 * 11 + 60 * 17 + 12,
        privileged=True,
        total_price_credits=Decimal("150"),
        price_credits_per_hour=Decimal("15"),
        priority=JobPriority.HIGH,
        energy_schedule_name="some-energy-schedule-name",
    )
    assert _job_to_cli_args(job) == [
        "--preset",
        "testing",
        "--no-extshm",
        "--name",
        "test-job",
        "--tag",
        "tag-1",
        "--tag",
        "tag-2",
        "--description",
        "'test description'",
        "--volume",
        "storage://test-cluster/test-user/_ro_:/mnt/_ro_:ro",
        "--volume",
        "storage://test-cluster/test-user/rw:/mnt/rw:rw",
        "--volume",
        "disk://test-cluster/test-user/disk1:/mnt/disk1:ro",
        "--volume",
        "disk://test-cluster/otheruser/disk2:/mnt/disk2:rw",
        "--volume",
        "secret://test-cluster/test-user/secret1:/var/run/secret1",
        "--volume",
        "secret://test-cluster/otheruser/secret2:/var/run/secret2",
        "--workdir",
        "/mnt/test",
        "--env",
        "ENV_NAME_3=TEST1",
        "--env",
        "ENV_NAME_4=TEST2",
        "--env",
        "ENV_NAME_1=secret://test-cluster/test-user/secret4",
        "--env",
        "ENV_NAME_2=secret://test-cluster/otheruser/secret5",
        "--restart",
        "always",
        "--life-span",
        "3m20s",
        "--schedule-timeout",
        "2d11h17m12s",
        "--pass-config",
        "--privileged",
        "--priority",
        "high",
        "--energy-schedule",
        "some-energy-schedule-name",
        "--project",
        "myproject",
        "test-image",
        "--",
        "test-command",
    ]


def test_job_to_args_no_cmd() -> None:
    job = JobDescription(
        status=JobStatus.FAILED,
        owner="test-user",
        project_name="proj",
        cluster_name="default",
        org_name="my_org",
        namespace="",
        id=f"job",
        uri=URL(f"job://default/test-user/job"),
        description=None,
        history=JobStatusHistory(
            status=JobStatus.FAILED,
            reason="ErrorReason",
            description="ErrorDesc",
            created_at=isoparse("2018-09-25T12:28:21.298672+00:00"),
            started_at=isoparse("2018-09-25T12:28:59.759433+00:00"),
            finished_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        ),
        container=Container(
            image=RemoteImage.new_external_image(name="test-image"),
            resources=Resources(memory=16, cpu=0.1, shm=True),
        ),
        scheduler_enabled=False,
        pass_config=False,
        preset_name="testing",
        total_price_credits=Decimal("150"),
        price_credits_per_hour=Decimal("15"),
    )
    assert _job_to_cli_args(job) == [
        "--preset",
        "testing",
        "--project",
        "proj",
        "test-image",
    ]
