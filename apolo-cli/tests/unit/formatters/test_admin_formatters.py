from datetime import datetime
from decimal import Decimal
from typing import Callable

from dateutil.parser import isoparse
from neuro_config_client import OrchestratorConfig
from rich.console import RenderableType

from apolo_sdk import (
    _AMDGPU,
    _Balance,
    _Cluster,
    _ClusterUser,
    _ClusterUserRoleType,
    _ClusterUserWithInfo,
    _ConfigCluster,
    _NvidiaGPU,
    _OrgCluster,
    _OrgUserRoleType,
    _OrgUserWithInfo,
    _Quota,
    _ResourcePoolType,
    _UserInfo,
)

from apolo_cli.formatters.admin import (
    ClustersFormatter,
    ClusterUserFormatter,
    ClusterUserWithInfoFormatter,
    OrgClusterFormatter,
    OrgUserFormatter,
)

RichCmp = Callable[[RenderableType], None]


class TestClusterUserFormatter:
    def test_list_users_with_user_info(self, rich_cmp: RichCmp) -> None:
        formatter = ClusterUserWithInfoFormatter()
        users = [
            _ClusterUserWithInfo(
                user_name="denis",
                cluster_name="default",
                org_name=None,
                role=_ClusterUserRoleType("admin"),
                quota=_Quota(),
                balance=_Balance(),
                user_info=_UserInfo(
                    first_name="denis",
                    last_name="admin",
                    email="denis@domain.name",
                    created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
                ),
            ),
            _ClusterUserWithInfo(
                user_name="andrew",
                cluster_name="default",
                org_name=None,
                role=_ClusterUserRoleType("manager"),
                quota=_Quota(),
                balance=_Balance(credits=Decimal(100)),
                user_info=_UserInfo(
                    first_name="andrew",
                    last_name=None,
                    email="andrew@domain.name",
                    created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
                ),
            ),
            _ClusterUserWithInfo(
                user_name="ivan",
                cluster_name="default",
                org_name=None,
                role=_ClusterUserRoleType("user"),
                quota=_Quota(total_running_jobs=1),
                balance=_Balance(),
                user_info=_UserInfo(
                    first_name=None,
                    last_name="user",
                    email="ivan@domain.name",
                    created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
                ),
            ),
            _ClusterUserWithInfo(
                user_name="alex",
                cluster_name="default",
                org_name=None,
                role=_ClusterUserRoleType("user"),
                quota=_Quota(total_running_jobs=2),
                balance=_Balance(credits=Decimal(100), spent_credits=Decimal(20)),
                user_info=_UserInfo(
                    first_name=None,
                    last_name=None,
                    email="alex@domain.name",
                    created_at=None,
                ),
            ),
            _ClusterUserWithInfo(
                user_name="alex",
                cluster_name="default",
                org_name="some-org",
                role=_ClusterUserRoleType("user"),
                quota=_Quota(total_running_jobs=2),
                balance=_Balance(credits=Decimal(100), spent_credits=Decimal(20)),
                user_info=_UserInfo(
                    first_name=None,
                    last_name=None,
                    email="alex@domain.name",
                    created_at=None,
                ),
            ),
        ]
        rich_cmp(formatter(users))

    def test_list_users_no_user_info(self, rich_cmp: RichCmp) -> None:
        formatter = ClusterUserFormatter()
        users = [
            _ClusterUser("default", "denis", None, _Quota(), _Balance(), None),
            _ClusterUser("default", "denis", None, _Quota(), _Balance(), "Org"),
            _ClusterUser("default", "andrew", None, _Quota(), _Balance(), None),
            _ClusterUser("default", "andrew", None, _Quota(), _Balance(), "Org"),
        ]
        rich_cmp(formatter(users))


class TestClustersFormatter:
    def _create_resource_pool(
        self,
        name: str,
        is_scalable: bool = True,
        is_gpu: bool = False,
        is_preemptible: bool = False,
        has_idle: bool = False,
    ) -> _ResourcePoolType:
        return _ResourcePoolType(
            name=name,
            min_size=1 if is_scalable else 2,
            max_size=2,
            idle_size=1 if has_idle else 0,
            cpu=8.0,
            available_cpu=7.0,
            memory=51200 * 2**20,
            available_memory=46080 * 2**20,
            disk_size=150 * 2**30,
            available_disk_size=100 * 2**30,
            nvidia_gpu=(
                _NvidiaGPU(count=1, model="nvidia-tesla-k80", memory=20 * 2**30)
                if is_gpu
                else None
            ),
            amd_gpu=(
                _AMDGPU(count=1, model="instinct-mi25", memory=20 * 2**30)
                if is_gpu
                else None
            ),
            is_preemptible=is_preemptible,
        )

    def test_cluster_list(self, rich_cmp: RichCmp) -> None:
        formatter = ClustersFormatter()
        clusters = {
            "default": (
                _Cluster(
                    name="default",
                    default_credits=Decimal(20),
                    default_quota=_Quota(total_running_jobs=42),
                    default_role=_ClusterUserRoleType.USER,
                ),
                _ConfigCluster(
                    name="default",
                    status=None,  # type: ignore
                    created_at=datetime(2022, 12, 3),
                ),
            )
        }
        rich_cmp(formatter(clusters))

    def test_cluster_with_minimum_node_pool_properties_list(
        self, rich_cmp: RichCmp
    ) -> None:
        formatter = ClustersFormatter()
        clusters = {
            "default": (
                _Cluster(
                    name="default",
                    default_credits=None,
                    default_quota=_Quota(),
                    default_role=_ClusterUserRoleType.USER,
                ),
                _ConfigCluster(
                    name="default",
                    status=None,  # type: ignore
                    orchestrator=OrchestratorConfig(
                        job_hostname_template="",
                        job_fallback_hostname="",
                        job_schedule_timeout_s=0,
                        job_schedule_scale_up_timeout_s=0,
                        resource_pool_types=[
                            self._create_resource_pool(
                                "node-pool-1", is_scalable=False
                            ),
                            self._create_resource_pool(
                                "node-pool-2", is_scalable=False, is_gpu=True
                            ),
                        ],
                    ),
                    created_at=datetime(2022, 12, 3),
                ),
            )
        }
        rich_cmp(formatter(clusters))

    def test_cluster_with_maximum_node_pool_properties_list(
        self, rich_cmp: RichCmp
    ) -> None:
        formatter = ClustersFormatter()
        clusters = {
            "default": (
                _Cluster(
                    name="default",
                    default_credits=None,
                    default_quota=_Quota(),
                    default_role=_ClusterUserRoleType.USER,
                ),
                _ConfigCluster(
                    name="default",
                    status=None,  # type: ignore
                    orchestrator=OrchestratorConfig(
                        job_hostname_template="",
                        job_fallback_hostname="",
                        job_schedule_timeout_s=0,
                        job_schedule_scale_up_timeout_s=0,
                        resource_pool_types=[
                            self._create_resource_pool(
                                "node-pool-1", is_preemptible=True, has_idle=True
                            ),
                            self._create_resource_pool("node-pool-2"),
                        ],
                    ),
                    created_at=datetime(2022, 12, 3),
                ),
            )
        }
        rich_cmp(formatter(clusters))


class TestOrgClusterFormatter:
    def test_org_cluster_formatter(self, rich_cmp: RichCmp) -> None:
        formatter = OrgClusterFormatter()
        cluster = _OrgCluster(
            cluster_name="test",
            org_name="test-org",
            quota=_Quota(total_running_jobs=2),
            balance=_Balance(credits=Decimal(100), spent_credits=Decimal(20)),
        )
        rich_cmp(formatter(cluster))

    def test_org_cluster_formatter_no_quota(self, rich_cmp: RichCmp) -> None:
        formatter = OrgClusterFormatter()
        cluster = _OrgCluster(
            cluster_name="test",
            org_name="test-org",
            quota=_Quota(),
            balance=_Balance(),
        )
        rich_cmp(formatter(cluster))


class TestOrgUserFormatter:
    def test_list_users_with_user_info(self, rich_cmp: RichCmp) -> None:
        formatter = OrgUserFormatter()
        users = [
            _OrgUserWithInfo(
                user_name="denis",
                org_name="org",
                role=_OrgUserRoleType("admin"),
                balance=_Balance(),
                user_info=_UserInfo(
                    first_name="denis",
                    last_name="admin",
                    email="denis@domain.name",
                    created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
                ),
            ),
            _OrgUserWithInfo(
                user_name="andrew",
                org_name="org",
                role=_OrgUserRoleType("manager"),
                balance=_Balance(credits=Decimal(100)),
                user_info=_UserInfo(
                    first_name="andrew",
                    last_name=None,
                    email="andrew@domain.name",
                    created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
                ),
            ),
            _OrgUserWithInfo(
                user_name="ivan",
                org_name="org",
                role=_OrgUserRoleType("user"),
                balance=_Balance(),
                user_info=_UserInfo(
                    first_name=None,
                    last_name="user",
                    email="ivan@domain.name",
                    created_at=isoparse("2017-03-04T12:28:59.759433+00:00"),
                ),
            ),
            _OrgUserWithInfo(
                user_name="alex",
                org_name="org",
                role=_OrgUserRoleType("user"),
                balance=_Balance(credits=Decimal(100), spent_credits=Decimal(20)),
                user_info=_UserInfo(
                    first_name=None,
                    last_name=None,
                    email="alex@domain.name",
                    created_at=None,
                ),
            ),
            _OrgUserWithInfo(
                user_name="alex",
                org_name="org",
                role=_OrgUserRoleType("user"),
                balance=_Balance(credits=Decimal(100), spent_credits=Decimal(20)),
                user_info=_UserInfo(
                    first_name=None,
                    last_name=None,
                    email="alex@domain.name",
                    created_at=None,
                ),
            ),
        ]
        rich_cmp(formatter(users))
