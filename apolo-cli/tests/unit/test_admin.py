from contextlib import ExitStack, contextmanager
from decimal import Decimal
from typing import Callable, Iterator, List, Mapping, Optional
from unittest import mock

from apolo_sdk import (
    Preset,
    _Admin,
    _Balance,
    _CloudProviderOptions,
    _CloudProviderType,
    _Clusters,
    _ClusterUser,
    _ClusterUserRoleType,
    _ClusterUserWithInfo,
    _NodePoolOptions,
    _OrgUserRoleType,
    _OrgUserWithInfo,
    _PatchNodePoolSizeRequest,
    _Quota,
    _ResourcePreset,
    _TPUPreset,
    _UserInfo,
)
from apolo_sdk._config import Config

from .conftest import SysCapWithCode

_RunCli = Callable[[List[str]], SysCapWithCode]


@contextmanager
def mock_create_cluster_user() -> Iterator[None]:
    with mock.patch.object(_Admin, "create_cluster_user") as mocked:

        async def create_cluster_user(
            cluster_name: str,
            user_name: str,
            role: _ClusterUserRoleType,
            quota: _Quota,
            org_name: Optional[str] = None,
        ) -> _ClusterUserWithInfo:
            # NOTE: We return a different role to check that we print it to user
            return _ClusterUserWithInfo(
                user_name=user_name,
                cluster_name=cluster_name,
                org_name=org_name,
                role=_ClusterUserRoleType.MANAGER,
                quota=quota,
                balance=_Balance(),
                user_info=_UserInfo(
                    email="some@email.com",
                    created_at=None,
                    first_name=None,
                    last_name=None,
                ),
            )

        mocked.side_effect = create_cluster_user
        yield


@contextmanager
def mock_create_org_user() -> Iterator[None]:
    with mock.patch.object(_Admin, "create_org_user") as mocked:

        async def create_org_user(
            org_name: str,
            user_name: str,
            role: _OrgUserRoleType,
            balance: _Balance,
        ) -> _OrgUserWithInfo:
            return _OrgUserWithInfo(
                user_name=user_name,
                org_name=org_name,
                role=role,
                balance=balance,
                user_info=_UserInfo(
                    email="some@email.com",
                    created_at=None,
                    first_name=None,
                    last_name=None,
                ),
            )

        mocked.side_effect = create_org_user
        yield


def test_add_cluster_user_print_result(run_cli: _RunCli) -> None:
    with mock_create_cluster_user():
        capture = run_cli(["admin", "add-cluster-user", "default", "ivan", "admin"])
    assert not capture.err
    assert "Added ivan to cluster default as manager" in capture.out
    assert "Jobs: unlimited" in capture.out
    assert capture.code == 0

    # Same with quiet mode
    with mock_create_cluster_user():
        capture = run_cli(
            ["-q", "admin", "add-cluster-user", "default", "ivan", "admin"]
        )
    assert not capture.err
    assert not capture.out
    assert capture.code == 0


def test_add_cluster_user_with_jobs(run_cli: _RunCli) -> None:
    for value in ("100", "0", "unlimited"):
        with mock_create_cluster_user():
            capture = run_cli(
                [
                    "admin",
                    "add-cluster-user",
                    "default",
                    "ivan",
                    "admin",
                    "--jobs",
                    value,
                ]
            )
        assert not capture.err
        assert capture.code == 0

    for value in ("spam", "-100", "10.5", "inf", "nan", "infinity", "Infinity"):
        with mock_create_cluster_user():
            capture = run_cli(
                [
                    "admin",
                    "add-cluster-user",
                    "default",
                    "ivan",
                    "admin",
                    "--jobs",
                    value,
                ]
            )
        assert f"jobs quota should be non-negative integer" in capture.err, capture
        assert capture.code == 2


def test_update_cluster_user(run_cli: _RunCli) -> None:
    with ExitStack() as exit_stack:

        async def get_cluster_user(
            cluster_name: str,
            user_name: str,
            org_name: Optional[str] = None,
        ) -> _ClusterUserWithInfo:
            return _ClusterUserWithInfo(
                cluster_name=cluster_name,
                user_name=user_name,
                role=_ClusterUserRoleType.USER,
                quota=_Quota(),
                balance=_Balance(),
                org_name=org_name,
                user_info=_UserInfo(email=f"{user_name}@example.org"),
            )

        mocked_get = exit_stack.enter_context(
            mock.patch.object(_Admin, "get_cluster_user")
        )
        mocked_get.side_effect = get_cluster_user

        async def update_cluster_user(
            cluster_user: _ClusterUser, with_user_info: bool = False
        ) -> _ClusterUser:
            return cluster_user

        mocked_update = exit_stack.enter_context(
            mock.patch.object(_Admin, "update_cluster_user")
        )
        mocked_update.side_effect = update_cluster_user

        capture = run_cli(
            ["admin", "update-cluster-user", "default", "test-user", "manager"]
        )

        assert capture.code == 0
        assert capture.out == "New role for user test-user on cluster default: manager"

        capture = run_cli(
            [
                "admin",
                "update-cluster-user",
                "default",
                "test-user",
                "manager",
                "--org",
                "test-org",
            ]
        )

        assert capture.code == 0
        assert capture.out == (
            "New role for user test-user as member of org test-org "
            "on cluster default: manager"
        )


def test_set_user_credits(run_cli: _RunCli) -> None:
    with mock.patch.object(_Admin, "update_org_user_balance") as mocked:

        async def update_org_user_balance(
            org_name: str,
            user_name: str,
            credits: Optional[Decimal],
        ) -> _OrgUserWithInfo:
            return _OrgUserWithInfo(
                org_name=org_name,
                user_name=user_name,
                role=_OrgUserRoleType.USER,
                balance=_Balance(credits=credits),
                user_info=_UserInfo(email=f"{user_name}@example.org"),
            )

        for value, outvalue in (
            ("1234.5", "1234.50"),
            ("0", "0.00"),
            ("-1234.5", "-1234.50"),
            ("unlimited", "unlimited"),
        ):
            mocked.side_effect = update_org_user_balance
            capture = run_cli(
                ["admin", "set-user-credits", "default", "ivan", "--credits", value]
            )
            assert not capture.err
            assert capture.out == (
                f"New credits for ivan as member of org default:\n"
                f"Credits: {outvalue}\n"
                f"Credits spent: 0.00"
            )
            assert capture.code == 0

        for value in ("spam", "inf", "nan", "infinity", "Infinity"):
            mocked.side_effect = update_org_user_balance
            capture = run_cli(
                ["admin", "set-user-credits", "default", "ivan", "--credits", value]
            )
            assert f"{value} is not valid decimal number" in capture.err
            assert capture.code == 2

        mocked.side_effect = update_org_user_balance
        capture = run_cli(["admin", "set-user-credits", "default", "ivan"])
        assert "Missing option '-c' / '--credits'." in capture.err
        assert capture.code == 2


def test_add_user_credits(run_cli: _RunCli) -> None:
    with mock.patch.object(_Admin, "update_org_user_balance_by_delta") as mocked:

        async def update_org_user_balance_by_delta(
            org_name: str,
            user_name: str,
            delta: Decimal,
        ) -> _OrgUserWithInfo:
            return _OrgUserWithInfo(
                org_name=org_name,
                user_name=user_name,
                role=_OrgUserRoleType.USER,
                balance=_Balance(credits=100 + delta),
                user_info=_UserInfo(email=f"{user_name}@example.org"),
            )

        for value, outvalue in (
            ("1234.5", "1334.50"),
            ("0", "100.00"),
            ("-1234.5", "-1134.50"),
        ):
            mocked.side_effect = update_org_user_balance_by_delta
            capture = run_cli(
                ["admin", "add-user-credits", "default", "ivan", "--credits", value]
            )
            assert not capture.err
            assert capture.out == (
                f"New credits for ivan as member of org default:\n"
                f"Credits: {outvalue}\n"
                f"Credits spent: 0.00"
            )
            assert capture.code == 0

        for value in ("spam", "unlimited", "inf", "nan", "infinity", "Infinity"):
            mocked.side_effect = update_org_user_balance_by_delta
            capture = run_cli(
                ["admin", "add-user-credits", "default", "ivan", "--credits", value]
            )
            assert f"{value} is not valid decimal number" in capture.err
            assert capture.code == 2

        mocked.side_effect = update_org_user_balance_by_delta
        capture = run_cli(["admin", "add-user-credits", "default", "ivan"])
        assert "Missing option '-c' / '--credits'." in capture.err
        assert capture.code == 2


def test_set_user_quota(run_cli: _RunCli) -> None:
    with mock.patch.object(_Admin, "update_cluster_user_quota") as mocked:

        async def update_cluster_user_quota(
            cluster_name: str,
            user_name: str,
            quota: _Quota,
            org_name: Optional[str] = None,
        ) -> _ClusterUserWithInfo:
            return _ClusterUserWithInfo(
                cluster_name=cluster_name,
                user_name=user_name,
                role=_ClusterUserRoleType.USER,
                quota=quota,
                balance=_Balance(),
                org_name=org_name,
                user_info=_UserInfo(email=f"{user_name}@example.org"),
            )

        for value in ("100", "0", "unlimited"):
            mocked.side_effect = update_cluster_user_quota
            capture = run_cli(
                ["admin", "set-user-quota", "default", "ivan", "--jobs", value]
            )
            assert not capture.err
            assert (
                capture.out == f"New quotas for ivan on cluster default:\nJobs: {value}"
            )
            assert capture.code == 0

        for value in ("spam", "-100", "10.5", "inf", "nan", "infinity", "Infinity"):
            mocked.side_effect = update_cluster_user_quota
            capture = run_cli(
                ["admin", "set-user-quota", "default", "ivan", "--jobs", value]
            )
            assert "jobs quota should be non-negative integer" in capture.err
            assert capture.code == 2

        mocked.side_effect = update_cluster_user_quota
        capture = run_cli(["admin", "set-user-quota", "default", "ivan"])
        assert "Missing option '-j' / '--jobs'." in capture.err
        assert capture.code == 2


def test_remove_cluster_user_print_result(run_cli: _RunCli) -> None:
    with mock.patch.object(_Admin, "delete_cluster_user") as mocked:

        async def delete_cluster_user(
            cluster_name: str,
            user_name: str,
            org_name: Optional[str] = None,
        ) -> None:
            return

        mocked.side_effect = delete_cluster_user
        capture = run_cli(["admin", "remove-cluster-user", "default", "ivan"])
        assert not capture.err
        assert capture.out == "Removed ivan from cluster default"

        # Same with quiet mode
        mocked.side_effect = delete_cluster_user
        capture = run_cli(["-q", "admin", "remove-cluster-user", "default", "ivan"])
        assert not capture.err
        assert not capture.out


def test_show_cluster_config_options(run_cli: _RunCli) -> None:
    with mock.patch.object(_Clusters, "get_cloud_provider_options") as mocked:
        sample_data = _CloudProviderOptions(
            type=_CloudProviderType.AWS,
            node_pools=[
                _NodePoolOptions(
                    machine_type="p2.xlarge",
                    cpu=4,
                    available_cpu=3,
                    memory=64 * 2**30,
                    available_memory=60 * 2**30,
                    nvidia_gpu=1,
                    nvidia_gpu_model="nvidia-tesla-k80",
                )
            ],
        )

        async def get_cloud_provider_options(
            cloud_provider_name: str,
        ) -> _CloudProviderOptions:
            assert cloud_provider_name == "aws"
            return sample_data

        mocked.side_effect = get_cloud_provider_options
        capture = run_cli(["admin", "show-cluster-options", "--type", "aws"])
        assert not capture.err


def test_add_resource_preset(run_cli: _RunCli) -> None:
    with ExitStack() as exit_stack:
        clusters_mocked = exit_stack.enter_context(
            mock.patch.object(_Clusters, "add_resource_preset")
        )
        config_mocked = exit_stack.enter_context(mock.patch.object(Config, "fetch"))

        async def add_resource_preset(
            cluster_name: str, preset: _ResourcePreset
        ) -> None:
            assert cluster_name == "default"
            assert preset == _ResourcePreset(
                name="cpu-micro",
                credits_per_hour=Decimal("10"),
                cpu=0.1,
                memory=100 * 10**6,
                nvidia_gpu=1,
                amd_gpu=2,
                intel_gpu=3,
                tpu=_TPUPreset(
                    type="v2-8",
                    software_version="1.14",
                ),
                scheduler_enabled=True,
                preemptible_node=True,
            )

        async def fetch() -> None:
            pass

        clusters_mocked.side_effect = add_resource_preset
        config_mocked.side_effect = fetch

        capture = run_cli(
            [
                "admin",
                "add-resource-preset",
                "cpu-micro",
                "--credits-per-hour",
                "10.00",
                "-c",
                "0.1",
                "-m",
                "100Mb",
                "-g",
                "1",
                "--amd-gpu",
                "2",
                "--intel-gpu",
                "3",
                "--tpu-type",
                "v2-8",
                "--tpu-sw-version",
                "1.14",
                "-p",
                "--preemptible-node",
            ]
        )
        assert capture.code == 0, capture.out + capture.err


def test_add_existing_resource_preset_not_allowed(run_cli: _RunCli) -> None:
    with ExitStack() as exit_stack:
        clusters_mocked = exit_stack.enter_context(
            mock.patch.object(_Clusters, "add_resource_preset")
        )
        config_mocked = exit_stack.enter_context(mock.patch.object(Config, "fetch"))

        async def add_resource_preset(
            cluster_name: str, presets: Mapping[str, Preset]
        ) -> None:
            pass

        async def fetch() -> None:
            pass

        clusters_mocked.side_effect = add_resource_preset
        config_mocked.side_effect = fetch

        capture = run_cli(
            [
                "admin",
                "add-resource-preset",
                "cpu-small",
            ]
        )
        assert capture.code == 127, capture.out + capture.err
        assert "Preset 'cpu-small' already exists" in capture.err


def test_update_resource_preset(run_cli: _RunCli) -> None:
    preset: Optional[Preset] = None

    with ExitStack() as exit_stack:
        clusters_mocked = exit_stack.enter_context(
            mock.patch.object(_Clusters, "update_resource_preset")
        )
        config_mocked = exit_stack.enter_context(mock.patch.object(Config, "fetch"))

        async def update_resource_preset(cluster_name: str, p: _ResourcePreset) -> None:
            assert cluster_name == "default"
            assert p.name == "cpu-small"
            nonlocal preset
            preset = Preset(
                credits_per_hour=p.credits_per_hour,
                cpu=p.cpu,
                memory=p.memory,
                nvidia_gpu=p.nvidia_gpu,
                amd_gpu=p.amd_gpu,
                intel_gpu=p.intel_gpu,
                nvidia_gpu_model=p.nvidia_gpu_model,
                amd_gpu_model=p.amd_gpu_model,
                intel_gpu_model=p.intel_gpu_model,
                tpu_type=p.tpu.type if p.tpu else None,
                tpu_software_version=p.tpu.software_version if p.tpu else None,
                preemptible_node=p.preemptible_node,
                scheduler_enabled=p.scheduler_enabled,
            )

        async def fetch() -> None:
            pass

        clusters_mocked.side_effect = update_resource_preset
        config_mocked.side_effect = fetch

        capture = run_cli(
            [
                "admin",
                "update-resource-preset",
                "cpu-small",
                "--credits-per-hour",
                "122.00",
            ]
        )
        assert capture.code == 0, capture.out + capture.err
        assert preset == Preset(
            credits_per_hour=Decimal("122.00"), cpu=7, memory=2 * 2**30
        )

        capture = run_cli(
            [
                "admin",
                "update-resource-preset",
                "cpu-small",
                "--credits-per-hour",
                "122.00",
                "-c",
                "0.1",
                "-m",
                "100Mb",
                "-g",
                "1",
                "--amd-gpu",
                "2",
                "--intel-gpu",
                "3",
                "--nvidia-gpu-model",
                "nvidia-tesla-k80",
                "--amd-gpu-model",
                "instinct-mi25",
                "--intel-gpu-model",
                "flex-170",
                "--tpu-type",
                "v2-8",
                "--tpu-sw-version",
                "1.14",
                "-p",
                "--preemptible-node",
            ]
        )
        assert capture.code == 0, capture.out + capture.err
        assert preset == Preset(
            credits_per_hour=Decimal("122.00"),
            cpu=0.1,
            memory=10**8,
            scheduler_enabled=True,
            preemptible_node=True,
            nvidia_gpu=1,
            amd_gpu=2,
            intel_gpu=3,
            nvidia_gpu_model="nvidia-tesla-k80",
            amd_gpu_model="instinct-mi25",
            intel_gpu_model="flex-170",
            tpu_type="v2-8",
            tpu_software_version="1.14",
        )


def test_add_resource_preset_print_result(run_cli: _RunCli) -> None:
    with ExitStack() as exit_stack:
        clusters_mocked = exit_stack.enter_context(
            mock.patch.object(_Clusters, "add_resource_preset")
        )
        config_mocked = exit_stack.enter_context(mock.patch.object(Config, "fetch"))

        async def add_resource_preset(
            cluster_name: str, preset: _ResourcePreset
        ) -> None:
            pass

        async def fetch() -> None:
            pass

        clusters_mocked.side_effect = add_resource_preset
        config_mocked.side_effect = fetch

        capture = run_cli(["admin", "add-resource-preset", "cpu-micro"])
        assert not capture.err
        assert capture.out == "Added resource preset cpu-micro in cluster default"

        # Same with quiet mode
        capture = run_cli(["-q", "admin", "add-resource-preset", "cpu-micro-2"])
        assert not capture.err
        assert not capture.out


def test_remove_resource_preset_print_result(run_cli: _RunCli) -> None:
    with ExitStack() as exit_stack:
        clusters_mocked = exit_stack.enter_context(
            mock.patch.object(_Clusters, "remove_resource_preset")
        )
        config_mocked = exit_stack.enter_context(mock.patch.object(Config, "fetch"))

        async def remove_resource_preset(cluster_name: str, preset_name: str) -> None:
            pass

        async def fetch() -> None:
            pass

        clusters_mocked.side_effect = remove_resource_preset
        config_mocked.side_effect = fetch

        capture = run_cli(["admin", "remove-resource-preset", "cpu-small"])
        assert not capture.err
        assert capture.out == "Removed resource preset cpu-small from cluster default"

        # Same with quiet mode
        capture = run_cli(["-q", "admin", "remove-resource-preset", "cpu-large"])
        assert not capture.err
        assert not capture.out


def test_remove_resource_preset_not_exists(run_cli: _RunCli) -> None:
    with ExitStack() as exit_stack:
        clusters_mocked = exit_stack.enter_context(
            mock.patch.object(_Clusters, "remove_resource_preset")
        )
        config_mocked = exit_stack.enter_context(mock.patch.object(Config, "fetch"))

        async def remove_resource_preset(cluster_name: str, preset_name: str) -> None:
            pass

        async def fetch() -> None:
            pass

        clusters_mocked.side_effect = remove_resource_preset
        config_mocked.side_effect = fetch

        capture = run_cli(["admin", "remove-resource-preset", "unknown"])
        assert capture.code
        assert "Preset 'unknown' not found" in capture.err


def test_update_node_pool(run_cli: _RunCli) -> None:
    with ExitStack() as exit_stack:
        clusters_mocked = exit_stack.enter_context(
            mock.patch.object(_Clusters, "update_node_pool")
        )

        async def update_node_pool(
            cluster_name: str, node_pool_name: str, request: _PatchNodePoolSizeRequest
        ) -> None:
            assert cluster_name == "default"
            assert node_pool_name == "cpu"
            assert request.idle_size == 1

        clusters_mocked.side_effect = update_node_pool

        capture = run_cli(
            ["admin", "update-node-pool", "default", "cpu", "--idle-size", "1"]
        )
        assert not capture.err
        assert capture.out == "Cluster default node pool cpu successfully updated"

        # Same with quiet mode
        capture = run_cli(
            ["-q", "admin", "update-node-pool", "default", "cpu", "--idle-size", "1"]
        )
        assert not capture.err
        assert not capture.out


def test_add_org_user_with_credits(run_cli: _RunCli) -> None:
    for value in ("1234.5", "0", "-1234.5", "unlimited"):
        with mock_create_org_user():
            capture = run_cli(
                [
                    "admin",
                    "add-org-user",
                    "default",
                    "ivan",
                    "admin",
                    "--credits",
                    value,
                ]
            )
        assert not capture.err
        assert capture.code == 0

    for value in ("spam", "inf", "nan", "infinity", "Infinity"):
        with mock_create_cluster_user():
            capture = run_cli(
                [
                    "admin",
                    "add-org-user",
                    "default",
                    "ivan",
                    "admin",
                    "--credits",
                    value,
                ]
            )
        assert f"{value} is not valid decimal number" in capture.err, capture
        assert capture.code == 2
