import logging
from typing import Any

import click
from rich.table import Table
from rich.text import Text
from yarl import URL

from apolo_sdk import Action, Permission, Share

from .formatters.utils import URIFormatter, uri_formatter
from .root import Root
from .utils import (
    alias,
    argument,
    command,
    group,
    option,
    parse_permission_action,
    parse_resource_for_sharing,
)

log = logging.getLogger(__name__)


@group()
def acl() -> None:
    """
    Access Control List management.
    """


@command()
@argument("uri")
@argument("user")
@argument("permission", type=click.Choice(["read", "write", "manage"]))
async def grant(root: Root, uri: str, user: str, permission: str) -> None:
    """
    Shares resource with another user.

    URI shared resource.

    USER username to share resource with.

    PERMISSION sharing access right: read, write, or manage.

    Examples:
    apolo acl grant storage:///sample_data/ alice manage
    apolo acl grant image:resnet50 bob read
    apolo acl grant job:///my_job_id alice write
    """
    try:
        uri_obj = parse_resource_for_sharing(uri, root)
        action_obj = parse_permission_action(permission)
        permission_obj = Permission(uri=uri_obj, action=action_obj)
        log.info(f"Using resource '{permission_obj.uri}'")

        actual_permission = await root.client.users.share(user, permission_obj)

        if actual_permission != permission_obj:
            log.warning(
                Text.assemble(
                    f"User already has higher permission: {actual_permission.action}"
                )
            )
        log.info("Grant succeeded")

    except ValueError as e:
        raise ValueError(f"Could not share resource '{uri}': {e}") from e


@command()
@argument("uri")
@argument("user")
async def revoke(root: Root, uri: str, user: str) -> None:
    """
    Revoke user access from another user.

    URI previously shared resource to revoke.

    USER to revoke URI resource from.

    Examples:
    apolo acl revoke storage:///sample_data/ alice
    apolo acl revoke image:resnet50 bob
    apolo acl revoke job:///my_job_id alice
    """
    try:
        uri_obj = parse_resource_for_sharing(uri, root)
        log.info(f"Using resource '{uri_obj}'")

        await root.client.users.revoke(user, uri_obj)

    except ValueError as e:
        raise ValueError(f"Could not unshare resource '{uri}': {e}") from e


@command()
@argument("uri", required=False)
@option(
    "-u",
    "username",
    default=None,
    help="Use specified user or role.",
)
@option(
    "--shared",
    is_flag=True,
    default=False,
    help="Output the resources shared by the user.",
)
@option("--full-uri", is_flag=True, help="Output full URI.")
async def ls(
    root: Root,
    uri: str | None,
    username: str | None,
    shared: bool,
    full_uri: bool,
) -> None:
    """
    List shared resources.

    The command displays a list of resources shared BY current user (default).

    To display a list of resources shared WITH current user apply --shared option.

    Examples:
    apolo acl list
    apolo acl list storage://
    apolo acl list --shared
    apolo acl list --shared image://
    """
    if username is None:
        username = root.client.username

    uri_fmtr: URIFormatter
    if full_uri:
        uri_fmtr = str
    else:
        uri_fmtr = uri_formatter(
            project_name=root.client.config.project_name_or_raise,
            cluster_name=root.client.cluster_name,
            org_name=root.client.config.org_name,
        )

    uri_obj = URL(uri) if uri else None

    if not shared:
        table = Table.grid(padding=(0, 2))
        table.add_column()  # URI
        table.add_column()  # Action

        with root.status("Fetching permissions"):
            permissions = await root.client.users.get_acl(
                username, scheme=None, uri=uri_obj
            )
        for p in sorted(permissions, key=_permission_key):
            table.add_row(uri_fmtr(p.uri), _fmt_action(p.action))
        with root.pager():
            root.print(table)
    else:
        table = Table.grid(padding=(0, 2))
        table.add_column()  # URI
        table.add_column()  # Action
        table.add_column()  # User

        with root.status("Fetching shares"):
            shares = await root.client.users.get_shares(
                username, scheme=None, uri=uri_obj
            )
        for share in sorted(shares, key=_shared_permission_key):
            table.add_row(
                uri_fmtr(share.permission.uri),
                _fmt_action(share.permission.action),
                share.user,
            )
        with root.pager():
            root.print(table)


def _permission_key(p: Permission) -> Any:
    return p.uri, p.action


def _shared_permission_key(share: Share) -> Any:
    return share.permission.uri, share.permission.action.value, share.user


ACTION_COLORS = {
    Action.READ: "blue",
    Action.WRITE: "green",
    Action.MANAGE: "bright_yellow",
}


def _fmt_action(action: Action) -> Text:
    color = ACTION_COLORS.get(action, "")
    return Text(action.value, style=color)


@command()
@option(
    "-u",
    "username",
    default=None,
    help="Fetch roles of specified user or role.",
)
async def list_roles(root: Root, username: str | None) -> None:
    """
    List roles.

    Examples:
    apolo acl list-roles
    apolo acl list-roles username/projects
    """
    with root.status("Fetching roles"):
        roles = await root.client.users.get_subroles(
            username or root.client.config.username
        )

    table = Table.grid(padding=(0, 2))
    table.add_column()  # Role
    for role in sorted(roles):
        table.add_row(role)
    with root.pager():
        root.print(table)


@command()
@argument("role_name")
async def add_role(root: Root, role_name: str) -> None:
    """
    Add new role.

    Examples:
    apolo acl add-role mycompany/subdivision
    """
    await root.client.users.add(role_name)


@command()
@argument("role_name")
async def remove_role(root: Root, role_name: str) -> None:
    """
    Remove existing role.

    Examples:
    apolo acl remove-role mycompany/subdivision
    """
    await root.client.users.remove(role_name)


acl.add_command(grant)
acl.add_command(revoke)
acl.add_command(ls)
acl.add_command(list_roles)
acl.add_command(add_role)
acl.add_command(remove_role)
acl.add_command(alias(ls, "list", help=ls.help, hidden=True))
