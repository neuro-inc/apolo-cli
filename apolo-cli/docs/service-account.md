# service-account

Operations with service accounts

Use `apolo service-account` to manage service accounts in Apolo.

Service accounts are non-human identities for automation, integrations, API clients, and external collaborators.

Service account access is managed in Apolo. The token is created by Apolo and must be stored securely.

## Usage

```bash
apolo service-account [OPTIONS] COMMAND [ARGS]...
```

Operations with service accounts.

Commands:

| Usage | Description |
| --- | --- |
| `create` | Create a service account |
| `get` | Get service account `SERVICE_ACCOUNT` |
| `ls` | List service accounts |
| `rm` | Remove service accounts `SERVICE_ACCOUNT` |

### create

Create a service account


#### Usage

```bash
apolo service-account create [OPTIONS]
```

Create a service account.

The `create` command returns the service account object and the token during creation.

The token is only shown at creation time. Store it securely.

The token can be obtained through:

- Apolo CLI
- Apolo SDK

The CLI exposes two token forms:

- a full passed-config token, which can be used as `APOLO_PASSED_CONFIG`
- a raw auth token, which can be used with `apolo config login-with-token`

### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |
| `--default-cluster CLUSTER` | Service account default cluster. Current cluster will be used if not specified. |
| `--default-org ORG` | Service account default organization. Current org will be used if not specified. |
| `--default-project PROJECT` | Service account default project. Current project will be used if not specified. |
| `--name NAME` | Optional service account name. |

### get

Get service account `SERVICE_ACCOUNT`

#### Usage

```bash
apolo service-account get [OPTIONS] SERVICE_ACCOUNT
```

Get service account `SERVICE_ACCOUNT`.

The output includes the backing role used for ACL grants.

#### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |

# ls

List service accounts

#### Usage

```bash
apolo service-account ls [OPTIONS]
```

List service accounts.

#### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |

### rm

Remove service accounts `SERVICE_ACCOUNT`

#### Usage

```bash
apolo service-account rm [OPTIONS] SERVICE_ACCOUNTS...
```

Remove service accounts `SERVICE_ACCOUNT`.

Removing a service account revokes access tied to it.

#### Options

| Name | Description |
| --- | --- |
| `--help` | Show this message and exit. |

### Notes

Use the token only after creation and store it in a secure secret store.

Do not rely on GitBook or any other documentation system to hold the token value.

If you need to hand the token to an external client, use a secure channel.
