from collections.abc import Sequence

from apolo_cli.click_types import CLUSTER, ORG, PROJECT, SERVICE_ACCOUNT
from apolo_cli.formatters.service_accounts import (
    BaseServiceAccountsFormatter,
    ServiceAccountFormatter,
    ServiceAccountsFormatter,
    SimpleServiceAccountsFormatter,
    service_account_token_fmtr,
)
from apolo_cli.formatters.utils import get_datetime_formatter

from .root import Root
from .utils import argument, command, group, option


@group()
def service_account() -> None:
    """
    Operations with service accounts.
    """


@command()
async def ls(root: Root) -> None:
    """
    List service accounts.
    """

    if root.quiet:
        fmtr: BaseServiceAccountsFormatter = SimpleServiceAccountsFormatter()
    else:
        fmtr = ServiceAccountsFormatter(
            datetime_formatter=get_datetime_formatter(root.iso_datetime_format)
        )

    accounts = []
    with root.status("Fetching service accounts") as status:
        async with root.client.service_accounts.list() as it:
            async for account in it:
                accounts.append(account)
                status.update(f"Fetching service accounts ({len(accounts)} loaded)")

    with root.pager():
        root.print(fmtr(accounts))


@command()
@option(
    "--name",
    metavar="NAME",
    help="Optional service account name",
    default=None,
)
@option(
    "--default-cluster",
    type=CLUSTER,
    help="Service account default cluster. Current cluster will"
    " be used if not specified",
    default=None,
)
@option(
    "--default-org",
    type=ORG,
    help="Service account default organization. Current org will"
    " be used if not specified",
    default=None,
)
@option(
    "--default-project",
    type=PROJECT,
    help="Service account default project. Current project will"
    " be used if not specified",
    default=None,
)
async def create(
    root: Root,
    name: str | None,
    default_cluster: str | None,
    default_org: str | None,
    default_project: str | None,
) -> None:
    """
    Create a service account.
    """

    account, token = await root.client.service_accounts.create(
        name=name,
        default_cluster=default_cluster,
        default_org=default_org,
        default_project=default_project,
    )
    fmtr = ServiceAccountFormatter(
        datetime_formatter=get_datetime_formatter(root.iso_datetime_format)
    )
    if root.quiet:
        root.print(token)
    else:
        # No pager here as it can make it harder to copy generated token
        root.print(fmtr(account))
        root.print("")
        root.print(service_account_token_fmtr(token, account), soft_wrap=True)


@command()
@argument("service_account", type=SERVICE_ACCOUNT)
async def get(root: Root, service_account: str) -> None:
    """
    Get service account SERVICE_ACCOUNT.
    """
    account = await root.client.service_accounts.get(service_account)

    fmtr = ServiceAccountFormatter(
        datetime_formatter=get_datetime_formatter(root.iso_datetime_format)
    )
    with root.pager():
        root.print(fmtr(account))


@command()
@argument("service_accounts", type=SERVICE_ACCOUNT, nargs=-1, required=True)
async def rm(root: Root, service_accounts: Sequence[str]) -> None:
    """
    Remove service accounts SERVICE_ACCOUNT.
    """
    for account in service_accounts:
        await root.client.service_accounts.rm(account)
        if root.verbosity >= 0:
            root.print(f"Service account '{account}' was successfully removed.")


service_account.add_command(ls)
service_account.add_command(create)
service_account.add_command(get)
service_account.add_command(rm)
