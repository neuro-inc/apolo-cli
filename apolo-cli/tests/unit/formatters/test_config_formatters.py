from dataclasses import replace
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Callable, Union

import pytest
import toml
from rich.console import RenderableType

from apolo_sdk import (
    Client,
    Cluster,
    Preset,
    Quota,
    _Balance,
    _ClusterStatus,
    _ConfigCluster,
    _EnergyConfig,
    _EnergySchedule,
    _EnergySchedulePeriod,
    _Quota,
)

from apolo_cli.alias import list_aliases
from apolo_cli.formatters.config import (
    AdminQuotaFormatter,
    AliasesFormatter,
    BalanceFormatter,
    ClusterOrgProjectsFormatter,
    ConfigFormatter,
    format_quota_details,
)
from apolo_cli.root import Root

RichCmp = Callable[[RenderableType], None]


@pytest.mark.parametrize(
    "quota,expected",
    [
        pytest.param(None, "unlimited", id="None->infinity"),
        pytest.param(0, "0", id="zero"),
        pytest.param(10, "10", id="int"),
        pytest.param(Decimal("1.23456"), "1.23", id="decimal"),
    ],
)
def test_format_quota_details(quota: Union[None, int, Decimal], expected: str) -> None:
    assert format_quota_details(quota) == expected


class TestConfigFormatter:
    async def test_output(self, root: Root, rich_cmp: RichCmp) -> None:
        out = ConfigFormatter()(
            root.client.config,
            {},
            Quota(credits=Decimal("500"), total_running_jobs=10),
            None,
        )
        rich_cmp(out)

    async def test_output_for_tpu_presets(
        self,
        make_client: Callable[..., Client],
        cluster_config: Cluster,
        rich_cmp: RichCmp,
    ) -> None:
        presets = dict(cluster_config.presets)

        presets["tpu-small"] = Preset(
            credits_per_hour=Decimal("10"),
            cpu=2,
            memory=2 * 2**30,
            scheduler_enabled=False,
            tpu_type="v3-8",
            tpu_software_version="1.14",
            resource_pool_names=("tpu",),
        )
        presets["hybrid"] = Preset(
            credits_per_hour=Decimal("10"),
            cpu=4,
            memory=30 * 2**30,
            scheduler_enabled=False,
            nvidia_gpu=1,
            amd_gpu=2,
            intel_gpu=3,
            nvidia_gpu_model="nvidia-tesla-k80",
            amd_gpu_model="instinct-mi25",
            intel_gpu_model="flex-170",
            tpu_type="v3-64",
            tpu_software_version="1.14",
            resource_pool_names=("gpu-small", "gpu-large"),
        )
        new_config = replace(cluster_config, presets=presets)

        client = make_client(
            "https://api.dev.apolo.us/api/v1", clusters={new_config.name: new_config}
        )
        out = ConfigFormatter()(
            client.config,
            {},
            Quota(credits=Decimal("500"), total_running_jobs=10),
            None,
        )
        rich_cmp(out)
        await client.close()

    async def test_output_with_jobs_available(
        self, root: Root, rich_cmp: RichCmp
    ) -> None:
        available_jobs_counts = {
            "cpu-small": 1,
            "cpu-large": 2,
        }
        out = ConfigFormatter()(
            root.client.config,
            available_jobs_counts,
            Quota(credits=Decimal("500"), total_running_jobs=10),
            None,
        )
        rich_cmp(out)

    async def test_output_with_org_quota(self, root: Root, rich_cmp: RichCmp) -> None:
        available_jobs_counts = {
            "cpu-small": 1,
            "cpu-large": 2,
        }
        out = ConfigFormatter()(
            root.client.config,
            available_jobs_counts,
            Quota(credits=Decimal("500"), total_running_jobs=10),
            Quota(credits=Decimal("1000"), total_running_jobs=50),
        )
        rich_cmp(out)

    async def test_output_without_project(
        self,
        make_client: Callable[..., Client],
        cluster_config: Cluster,
        rich_cmp: RichCmp,
    ) -> None:
        client = make_client(
            "https://api.dev.apolo.us/api/v1",
            clusters={cluster_config.name: cluster_config},
            projects={},
            project_name=None,
        )
        out = ConfigFormatter()(
            client.config,
            {},
            Quota(credits=Decimal("500"), total_running_jobs=10),
            None,
        )
        rich_cmp(out)

    @pytest.fixture
    def _config_cluster_with_energy(self) -> _ConfigCluster:
        return _ConfigCluster(
            name="default",
            status=_ClusterStatus.DEPLOYED,
            created_at=datetime.now(),
            energy=_EnergyConfig(
                co2_grams_eq_per_kwh=40.4,
                schedules=(
                    _EnergySchedule(
                        "DEFAULT",
                        price_per_kwh=Decimal("10.4"),
                        periods=(
                            _EnergySchedulePeriod(1, time.min, time.max),
                            _EnergySchedulePeriod(2, time.min, time.max),
                            _EnergySchedulePeriod(3, time.min, time.max),
                            _EnergySchedulePeriod(4, time.min, time.max),
                            _EnergySchedulePeriod(5, time.min, time.max),
                            _EnergySchedulePeriod(6, time.min, time.max),
                            _EnergySchedulePeriod(7, time.min, time.max),
                        ),
                    ),
                    _EnergySchedule(
                        "GREEN",
                        price_per_kwh=Decimal("0.5"),
                        periods=(
                            _EnergySchedulePeriod(1, time.min, time(8)),
                            _EnergySchedulePeriod(2, time.min, time(8)),
                            _EnergySchedulePeriod(3, time.min, time(8)),
                            _EnergySchedulePeriod(4, time.min, time(8)),
                            _EnergySchedulePeriod(5, time.min, time(8)),
                            _EnergySchedulePeriod(6, time.min, time(8)),
                            _EnergySchedulePeriod(7, time.min, time(8)),
                            _EnergySchedulePeriod(1, time(20), time.max),
                            _EnergySchedulePeriod(2, time(20), time.max),
                            _EnergySchedulePeriod(3, time(20), time.max),
                            _EnergySchedulePeriod(4, time(20), time.max),
                            _EnergySchedulePeriod(5, time(20), time.max),
                            _EnergySchedulePeriod(6, time(20), time.max),
                            _EnergySchedulePeriod(7, time(20), time.max),
                        ),
                    ),
                    _EnergySchedule(
                        "SCATTERED",
                        price_per_kwh=Decimal("0.5"),
                        periods=(
                            _EnergySchedulePeriod(1, time(5), time(10)),
                            _EnergySchedulePeriod(2, time(3), time(5)),
                            _EnergySchedulePeriod(3, time.min, time.max),
                            _EnergySchedulePeriod(4, time(5), time(10)),
                            _EnergySchedulePeriod(5, time(2), time(5)),
                            _EnergySchedulePeriod(6, time.min, time.max),
                            _EnergySchedulePeriod(7, time.min, time.max),
                        ),
                    ),
                ),
            ),
        )

    async def test_output_for_energy_schedules(
        self, root: Root, _config_cluster_with_energy: _ConfigCluster, rich_cmp: RichCmp
    ) -> None:
        out = ConfigFormatter()(
            root.client.config,
            {},
            Quota(credits=Decimal("500"), total_running_jobs=10),
            None,
            _config_cluster_with_energy,
        )
        rich_cmp(out)


bold_start = "\x1b[1m"
bold_end = "\x1b[0m"


class TestAdminQuotaFormatter:
    def test_output(self, rich_cmp: RichCmp) -> None:
        quota = _Quota(
            total_running_jobs=10,
        )
        out = AdminQuotaFormatter()(quota)
        rich_cmp(out)

    def test_output_no_quota(self, rich_cmp: RichCmp) -> None:
        quota = _Quota(
            total_running_jobs=None,
        )
        out = AdminQuotaFormatter()(quota)
        rich_cmp(out)

    def test_output_zeroes(self, rich_cmp: RichCmp) -> None:
        quota = _Quota(
            total_running_jobs=0,
        )
        out = AdminQuotaFormatter()(quota)
        rich_cmp(out)


class TestBalanceFormatter:
    def test_output(self, rich_cmp: RichCmp) -> None:
        balance = _Balance(credits=Decimal("10"), spent_credits=Decimal("0.23"))
        out = BalanceFormatter()(balance)
        rich_cmp(out)

    def test_output_no_quota(self, rich_cmp: RichCmp) -> None:
        balance = _Balance(
            credits=None,
        )
        out = BalanceFormatter()(balance)
        rich_cmp(out)

    def test_output_rounding(self, rich_cmp: RichCmp) -> None:
        balance = _Balance(credits=Decimal("10"), spent_credits=Decimal(1 / 3))
        out = BalanceFormatter()(balance)
        rich_cmp(out)


class TestAliasesFormatter:
    async def test_output(self, root: Root, nmrc_path: Path, rich_cmp: RichCmp) -> None:
        user_cfg = nmrc_path / "user.toml"
        user_cfg.write_text(
            toml.dumps(
                {
                    "alias": {
                        "lsl": {
                            "cmd": "storage ls -l",
                            "help": "Custom ls with long output.",
                        },
                        "user-cmd": {"exec": "script"},
                    }
                }
            )
        )
        lst = await list_aliases(root)
        out = AliasesFormatter()(lst)
        rich_cmp(out)


class TestClusterOrgProjectsFormatter:
    async def test_output(self, rich_cmp: RichCmp) -> None:
        projects = ["project1", "project2"]
        out = ClusterOrgProjectsFormatter()(projects, None)
        rich_cmp(out)

    async def test_output_with_current_project(self, rich_cmp: RichCmp) -> None:
        projects = ["project1", "project2"]
        out = ClusterOrgProjectsFormatter()(projects, "project1")
        rich_cmp(out)
