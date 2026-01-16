# vcluster

Operations with virtual kubernetes clusters

## Usage

```bash
apolo vcluster [OPTIONS] COMMAND [ARGS]...
```

Operations with virtual kubernetes clusters.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_activate-service-account_](vcluster.md#activate-service-account) | Activate kubernetes service account |
| [_create-service-account_](vcluster.md#create-service-account) | Create kubernetes service account |
| [_delete-service-account_](vcluster.md#delete-service-account) | Delete kubernetes service account |
| [_list-service-accounts_](vcluster.md#list-service-accounts) | List kubernetes service accounts |
| [_regenerate-service-account_](vcluster.md#regenerate-service-account) | Regenerate kubernetes service account |


### activate-service-account

Activate kubernetes service account


#### Usage

```bash
apolo vcluster activate-service-account [OPTIONS] NAME
```

Activate kubernetes service account

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### create-service-account

Create kubernetes service account


#### Usage

```bash
apolo vcluster create-service-account [OPTIONS] NAME
```

Create kubernetes service account

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |
| _--ttl TTL_ | Expiration time in the format '1y2m3d4h5m6s' \(some parts may be missing\). |



### delete-service-account

Delete kubernetes service account


#### Usage

```bash
apolo vcluster delete-service-account [OPTIONS] NAME
```

Delete kubernetes service account

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### list-service-accounts

List kubernetes service accounts


#### Usage

```bash
apolo vcluster list-service-accounts [OPTIONS]
```

List kubernetes service accounts

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--all-users_ | Show accounts for all project users. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--long-format_ | Output all info about service accounts. |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### regenerate-service-account

Regenerate kubernetes service account


#### Usage

```bash
apolo vcluster regenerate-service-account [OPTIONS] NAME
```

Regenerate kubernetes service account

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |
| _--ttl TTL_ | Expiration time in the format '1y2m3d4h5m6s' \(some parts may be missing\). |


