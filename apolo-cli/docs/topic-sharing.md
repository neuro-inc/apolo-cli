Using the sharing functionality
===============================

Understanding permissions
-------------------------

The Apolo platform supports five levels of access:

- `deny` - No access
- `list` - Permits listing entities, but not looking at their details
- `read` - Read-only access to an entity
- `write` - Read-write access to an entity, including deletion
- `manage` - Allows modification of an entity's permissions

Permissions are inclusive: `write` implies `read`, and `manage` includes `read` and `write`.

Permissions can be granted with `apolo acl grant` or `apolo share`, and revoked with `apolo acl revoke`.

```bash
apolo acl grant job:job-0a6d3f81-b5d2-45db-95e3-548cc1fac81a bob
apolo acl revoke job:job-0a6d3f81-b5d2-45db-95e3-548cc1fac81a bob
```

You can inspect entities owned by you and shared with you with `apolo acl list`.
This shows entity URIs and access levels.

Use `-s` to filter by entity type, for example `apolo acl list -s job`.

If the output contains a URI such as `secret:` or `storage:`, it means you have permissions for all entities of that type.

Use `apolo acl list --shared` to show entities shared by you together with the users or roles you shared them with.

Service accounts use the same sharing model.
The service account itself is backed by a role principal, and ACL grants are applied to that principal.
Share the service account token separately, and grant only the permissions needed by the backing role.

Roles
-----

The Apolo platform supports role-based access control.
A role is a packed set of permissions to multiple entities that can be shared together.

There are several default roles in each cluster, and users may additionally create their own custom roles.

Default roles are:

- `{cluster}/manager`
- `{cluster}/admin`
- `{cluster}/users/{username}` - created for every cluster user and always contains the user's full permission set

To create a new role, run:

```bash
apolo acl add-role {username}/roles/{rolename}
```

This creates a role named `rolename` with an empty permission set.
Then share resources with that role via `apolo acl grant`.

For example, to group access for a client or service account:

```bash
apolo acl grant image:IMAGE_NAME {username}/roles/{rolename}
apolo acl grant job:JOB_NAME {username}/roles/{rolename}
apolo acl grant job:ANOTHER_JOB_NAME {username}/roles/{rolename}
apolo acl grant storage:/folder_name {username}/roles/{rolename}
```

When ready, grant this permission set to another user:

```bash
apolo acl grant role://{username}/roles/{rolename} bob
```

From that point on, `bob` will have access to all entities listed under `{username}/roles/{rolename}`.
The list can be viewed with `apolo acl list -u {username}/roles/{rolename}`.

If needed, a role can be revoked:

```bash
apolo acl revoke role://{username}/roles/{rolename} bob
```

Roles can be deleted with:

```bash
apolo acl remove-role {username}/roles/{rolename}
```
