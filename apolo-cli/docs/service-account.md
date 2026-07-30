# service-account

Operations with service accounts

## Usage

```bash
apolo service-account [OPTIONS] COMMAND [ARGS]...
```

Operations with service accounts.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_create_](service-account.md#create) | Create a service account |
| [_get_](service-account.md#get) | Get service account SERVICE\_ACCOUNT |
| [_ls_](service-account.md#ls) | List service accounts |
| [_rm_](service-account.md#rm) | Remove service account SERVICE\_ACCOUNT |


### create

Create a service account


#### Usage

```bash
apolo service-account create [OPTIONS]
```

Create a service account.

The `create` command returns the service account
object
and the token during creation.
The token is only shown at creation
time. Store it securely.
If you need to hand the token to an external client,
use a secure channel.

The `CLI` exposes two token forms:
- a full passed-
config token, which can be used as ``APOLO`_`PASSED`_`CONFIG``
- a raw auth
token, which can be used with `apolo config login-with-token`

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--default-cluster CLUSTER_ | Service account default cluster. Current cluster will be used if not specified |
| _--default-org ORG_ | Service account default organization. Current org will be used if not specified |
| _--default-project PROJECT_ | Service account default project. Current project will be used if not specified |
| _--name NAME_ | Optional service account name |



### get

Get service account SERVICE_ACCOUNT


#### Usage

```bash
apolo service-account get [OPTIONS] SERVICE_ACCOUNT
```

Get service account `SERVICE`_`ACCOUNT`.

The output includes the backing role
used for `ACL` grants.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### ls

List service accounts


#### Usage

```bash
apolo service-account ls [OPTIONS]
```

List service accounts.

Service accounts are non-human identities for
automation, integrations,
`API` clients, and external collaborators.

Service
account access is managed in Apolo.
The token is created by Apolo and must be
stored securely.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### rm

Remove service account SERVICE_ACCOUNT


#### Usage

```bash
apolo service-account rm [OPTIONS] SERVICE_ACCOUNTS...
```

Remove service account `SERVICE`_`ACCOUNT`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |


