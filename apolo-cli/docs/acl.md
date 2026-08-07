# acl

Access Control List management

## Usage

```bash
apolo acl [OPTIONS] COMMAND [ARGS]...
```

Access Control List management.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_add-role_](acl.md#add-role) | Add new role |
| [_grant_](acl.md#grant) | Shares resource with another user |
| [_list-roles_](acl.md#list-roles) | List roles |
| [_ls_](acl.md#ls) | List shared resources |
| [_remove-role_](acl.md#remove-role) | Remove existing role |
| [_revoke_](acl.md#revoke) | Revoke previously shared resource access |


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
| :--- | :--- |
| _--help_ | Show this message and exit. |



### grant

Shares resource with another user


#### Usage

```bash
apolo acl grant [OPTIONS] URI USER {read|write|manage}
```

Shares resource with another user.

`URI` is the shared resource.

`USER` is
the username, role, or service account backing role principal to share with.
`PERMISSION` sharing access right: `read`, `write`, or `manage`.

#### Examples

```bash
$ apolo acl grant storage:///sample_data/ alice manage
$ apolo acl grant image:resnet50 bob read
$ apolo acl grant job:///my_job_id alice write
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### list-roles

List roles


#### Usage

```bash
apolo acl list-roles [OPTIONS]
```

List roles.

#### Examples

```bash
$ apolo acl list-roles
$ apolo acl list-roles username/projects
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-u TEXT_ | Fetch roles of specified user or role. |



### ls

List shared resources


#### Usage

```bash
apolo acl ls [OPTIONS] [URI]
```

List shared resources.

The command displays a list of resources available TO
current user (default).

To display a list of resources shared BY current
user, along with the users and
roles they are shared with, apply --shared
option.

Use `-u/--username` to fetch roles of a specified user or role.

#### Examples

```bash
$ apolo acl list
$ apolo acl list storage://
$ apolo acl list --shared
$ apolo acl list --shared image://
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--full-uri_ | Output full URI. |
| _--shared_ | Output the resources shared by the user. |
| _-u TEXT_ | Use specified user or role. |



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
| :--- | :--- |
| _--help_ | Show this message and exit. |



### revoke

Revoke previously shared resource access


#### Usage

```bash
apolo acl revoke [OPTIONS] URI USER
```

Revoke previously shared resource access.

`URI` is the shared resource to
revoke.

`USER` is the user, role, or service account backing role principal
to revoke access from.

Notes: Service accounts are commonly shared through
their backing role principal.
Use `read` for read-only image registry access
and reserve `manage`
for administrative workflows.

#### Examples

```bash
$ apolo acl revoke storage:///sample_data/ alice
$ apolo acl revoke image:resnet50 bob
$ apolo acl revoke job:///my_job_id alice
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |


