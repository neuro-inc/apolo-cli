# acl

Access Control List management

## Usage

```bash
apolo acl [OPTIONS] COMMAND [ARGS]...
```

Access Control List management.

Commands:

| Usage | Description |
| --- | --- |
| `add-role` | Add new role |
| `grant` | Shares resource with another user |
| `list-roles` | List roles |
| `ls` | List shared resources |
| `remove-role` | Remove existing role |
| `revoke` | Revoke user access from another user |


### add-role

Add new role


#### Usage

```bash
apolo acl add-role [OPTIONS] ROLE_NAME
```

Add new role.

#### Examples

```bash
$ apolo acl add-role mycompany/subdivision
```

#### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |


### grant

Shares resource with another user


#### Usage

```bash
apolo acl grant [OPTIONS] URI USER {read|write|manage}
```

Shares resource with another user.

`URI` is the shared resource.

`USER` is the username, role, or service account backing role principal to share with.

`PERMISSION` is the sharing access right: `read`, `write`, or `manage`.

#### Examples

```bash
apolo acl grant image:resnet50 bob read
apolo acl grant storage:///sample_data/ alice manage
apolo acl grant job:///my_job_id alice write
```

#### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |


### list-roles

List roles


#### Usage

```bash
apolo acl list-roles [OPTIONS]
```

List roles.

Use `-u` to fetch roles of a specified user or role.

### Examples

```bash
$ apolo acl list-roles
$ apolo acl list-roles username/projects
```

#### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |
| `-u TEXT` | Fetch roles of specified user or role. |


### ls

List shared resources


#### Usage

```bash
apolo acl ls [OPTIONS] [URI]
```

List shared resources.

The command displays resources shared by the current user by default.

Use `--shared` to display resources shared with the current user.

#### Examples

```bash
apolo acl list
apolo acl list storage://
apolo acl list --shared
apolo acl list --shared image://
```

#### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |
| `--full-uri` | Output full URI. |
| `--shared` | Output the resources shared by the user. |
| `-u TEXT` | Use specified user or role. |


### remove-role

Remove existing role


#### Usage

```bash
apolo acl remove-role [OPTIONS] ROLE_NAME
```

Remove existing role.

#### Examples

```bash
$ apolo acl remove-role mycompany/subdivision
```

#### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |


### revoke

Revoke user access from another user


#### Usage

```bash
apolo acl revoke [OPTIONS] URI USER
```

Revoke previously shared resource access.

`URI` is the shared resource to revoke.

`USER` is the user, role, or service account backing role principal to revoke access from.

#### Examples

```bash
apolo acl revoke storage:///sample_data/ alice
apolo acl revoke image:resnet50 bob
apolo acl revoke job:///my_job_id alice
```

#### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |

### Notes

Service accounts are commonly shared through their backing role principal.

Use `read` for read-only image registry access and reserve `manage` for administrative workflows.

