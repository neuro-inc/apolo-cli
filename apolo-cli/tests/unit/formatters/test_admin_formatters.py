from datetime import datetime
from decimal import Decimal
from typing import Callable

from dateutil.parser import isoparse
from rich.console import RenderableType

from apolo_sdk import (
    _Balance,
    _CloudProviderOptions,
    _CloudProviderType,
    _Cluster,
    _ClusterStatus,
    _ClusterUser,
    _ClusterUserRoleType,
    _ClusterUserWithInfo,
    _ConfigCluster,
    _GoogleCloudProvider,
    _GoogleFilestoreTier,
    _GoogleStorage,
    _NodePool,
    _NodePoolOptions,
    _OnPremCloudProvider,
    _OrgCluster,
    _OrgUserRoleType,
    _OrgUserWithInfo,
    _Quota,
    _StorageInstance,
    _UserInfo,
)

from apolo_cli.formatters.admin import (
    CloudProviderOptionsFormatter,
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
    def _create_node_pool(
        self,
        name: str,
        disk_type: str = "",
        is_scalable: bool = True,
        is_gpu: bool = False,
        is_preemptible: bool = False,
        has_idle: bool = False,
    ) -> _NodePool:
        return _NodePool(
            name=name,
            min_size=1 if is_scalable else 2,
            max_size=2,
            idle_size=1 if has_idle else 0,
            machine_type="n1-highmem-8",
            cpu=8.0,
            available_cpu=7.0,
            memory=51200 * 2**20,
            available_memory=46080 * 2**20,
            disk_size=150 * 2**30,
            available_disk_size=100 * 2**30,
            disk_type=disk_type,
            nvidia_gpu=1 if is_gpu else 0,
            nvidia_gpu_model="nvidia-tesla-k80" if is_gpu else None,
            amd_gpu=1 if is_gpu else 0,
            amd_gpu_model="instinct-mi25" if is_gpu else None,
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
                    status=_ClusterStatus.DEPLOYED,
                    created_at=datetime(2022, 12, 3),
                ),
            )
        }
        rich_cmp(formatter(clusters))

    def test_cluster_with_on_prem_cloud_provider_list(self, rich_cmp: RichCmp) -> None:
        formatter = ClustersFormatter()
        clusters = {
            "on-prem": (
                _Cluster(
                    name="on-prem",
                    default_credits=None,
                    default_quota=_Quota(),
                    default_role=_ClusterUserRoleType.USER,
                ),
                _ConfigCluster(
                    name="on-prem",
                    status=_ClusterStatus.DEPLOYED,
                    cloud_provider=_OnPremCloudProvider(
                        node_pools=[],
                        storage=None,
                    ),
                    created_at=datetime(2022, 12, 3),
                ),
            )
        }
        rich_cmp(formatter(clusters))

    def test_cluster_with_cloud_provider_storage_list(self, rich_cmp: RichCmp) -> None:
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
                    status=_ClusterStatus.DEPLOYED,
                    cloud_provider=_GoogleCloudProvider(
                        region="us-central1",
                        zones=["us-central1-a", "us-central1-c"],
                        project="apolo",
                        credentials={},
                        node_pools=[],
                        storage=_GoogleStorage(
                            description="Filestore",
                            tier=_GoogleFilestoreTier.STANDARD,
                            instances=[
                                _StorageInstance(name="org1", size=2**30),
                                _StorageInstance(name="org2", size=2 * 2**30),
                            ],
                        ),
                    ),
                    created_at=datetime(2022, 12, 3),
                ),
            )
        }
        rich_cmp(formatter(clusters))

    def test_cluster_with_cloud_provider_storage_without_size_list(
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
                    status=_ClusterStatus.DEPLOYED,
                    cloud_provider=_GoogleCloudProvider(
                        region="us-central1",
                        zones=["us-central1-a", "us-central1-c"],
                        project="apolo",
                        credentials={},
                        node_pools=[],
                        storage=_GoogleStorage(
                            description="Filestore",
                            tier=_GoogleFilestoreTier.STANDARD,
                            instances=[
                                _StorageInstance(name="org1"),
                                _StorageInstance(name="org2"),
                            ],
                        ),
                    ),
                    created_at=datetime(2022, 12, 3),
                ),
            )
        }
        rich_cmp(formatter(clusters))

    def test_cluster_with_cloud_provider_with_minimum_node_pool_properties_list(
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
                    status=_ClusterStatus.DEPLOYED,
                    cloud_provider=_OnPremCloudProvider(
                        node_pools=[
                            self._create_node_pool(
                                "node-pool-1", disk_type="", is_scalable=False
                            ),
                            self._create_node_pool(
                                "node-pool-2",
                                disk_type="ssd",
                                is_scalable=False,
                                is_gpu=True,
                            ),
                        ],
                        storage=None,
                    ),
                    created_at=datetime(2022, 12, 3),
                ),
            )
        }
        rich_cmp(formatter(clusters))

    def test_cluster_with_cloud_provider_with_maximum_node_pool_properties_list(
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
                    status=_ClusterStatus.DEPLOYED,
                    cloud_provider=_GoogleCloudProvider(
                        region="us-central1",
                        zones=[],
                        project="apolo",
                        credentials={},
                        node_pools=[
                            self._create_node_pool(
                                "node-pool-1", is_preemptible=True, has_idle=True
                            ),
                            self._create_node_pool("node-pool-2"),
                        ],
                        storage=None,
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


class TestCloudProviderOptionsFormatter:
    def test_formatter_aws(self, rich_cmp: RichCmp) -> None:
        formatter = CloudProviderOptionsFormatter()
        options = _CloudProviderOptions(
            type=_CloudProviderType.AWS,
            node_pools=[
                _NodePoolOptions(
                    machine_type="m5.xlarge",
                    cpu=4,
                    available_cpu=3,
                    memory=16 * 10**3,
                    available_memory=14 * 2**30,
                ),
                _NodePoolOptions(
                    machine_type="p2.xlarge",
                    cpu=4,
                    available_cpu=3,
                    memory=64 * 10**3,
                    available_memory=60 * 2**30,
                    nvidia_gpu=1,
                    nvidia_gpu_model="nvidia-tesla-k80",
                ),
            ],
        )
        rich_cmp(formatter(options))

    def test_formatter_gcp(self, rich_cmp: RichCmp) -> None:
        formatter = CloudProviderOptionsFormatter()
        options = _CloudProviderOptions(
            type=_CloudProviderType.GCP,
            node_pools=[
                _NodePoolOptions(
                    machine_type="n1-highmem-4",
                    cpu=4,
                    available_cpu=3,
                    memory=16 * 10**3,
                    available_memory=14 * 2**30,
                ),
                _NodePoolOptions(
                    machine_type="n1-highmem-4",
                    cpu=4,
                    available_cpu=3,
                    memory=64 * 10**3,
                    available_memory=60 * 2**30,
                    nvidia_gpu=1,
                    nvidia_gpu_model="nvidia-tesla-k80",
                ),
            ],
        )
        rich_cmp(formatter(options))

    def test_formatter_azure(self, rich_cmp: RichCmp) -> None:
        formatter = CloudProviderOptionsFormatter()
        options = _CloudProviderOptions(
            type=_CloudProviderType.AZURE,
            node_pools=[
                _NodePoolOptions(
                    machine_type="Standard_D4_v3",
                    cpu=4,
                    available_cpu=3,
                    memory=16 * 10**3,
                    available_memory=14 * 2**30,
                ),
                _NodePoolOptions(
                    machine_type="Standard_NC6",
                    cpu=4,
                    available_cpu=3,
                    memory=64 * 10**3,
                    available_memory=60 * 2**30,
                    nvidia_gpu=1,
                    nvidia_gpu_model="nvidia-tesla-k80",
                ),
            ],
        )
        rich_cmp(formatter(options))


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
