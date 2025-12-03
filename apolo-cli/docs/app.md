# app

Operations with applications

## Usage

```bash
apolo app [OPTIONS] COMMAND [ARGS]...
```

Operations with applications.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_configure_](app.md#configure) | Reconfigure an app instance using YAML file |
| [_get-status_](app.md#get-status) | Get status events for an app |
| [_get-values_](app.md#get-values) | Get application values |
| [_install_](app.md#install) | Install an app from a YAML file |
| [_list_](app.md#list) | List apps |
| [_logs_](app.md#logs) | Print the logs for an app |
| [_ls_](app.md#ls) | Alias to list |
| [_uninstall_](app.md#uninstall) | Uninstall an app |


### configure

Reconfigure an app instance using YAML file


#### Usage

```bash
apolo app configure [OPTIONS] APP_ID
```

Reconfigure an app instance using `YAML` file.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-f, --file TEXT_ | Path to the app configuration YAML file.  _\[required\]_ |



### get-status

Get status events for an app


#### Usage

```bash
apolo app get-status [OPTIONS] APP_ID
```

Get status events for an app.

`APP`_ID: ID of the app to get status for
status events.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _-o, --output \[table &#124; json\]_ | Output format \(default: table\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### get-values

Get application values


#### Usage

```bash
apolo app get-values [OPTIONS] [APP_ID]
```

Get application values.

`APP`_ID: Optional ID of the app to get values for.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _-o, --output TEXT_ | Output format \(default: table\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |
| _-t, --type TEXT_ | Filter by value type. |



### install

Install an app from a YAML file


#### Usage

```bash
apolo app install [OPTIONS]
```

Install an app from a `YAML` file.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Specify the cluster \(the current cluster by default\). |
| _-f, --file TEXT_ | Path to the app YAML file.  _\[required\]_ |
| _--org ORG_ | Specify the org \(the current org by default\). |
| _--project PROJECT_ | Specify the project \(the current project by default\). |



### list

List apps


#### Usage

```bash
apolo app list [OPTIONS]
```

List apps.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-a, --all_ | Show apps in all states. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |
| _-s, --state \[queued &#124; progressing &#124; healthy &#124; degraded &#124; errored &#124; uninstalling &#124; uninstalled\]_ | Filter out apps by state \(multiple option\). |



### logs

Print the logs for an app


#### Usage

```bash
apolo app logs [OPTIONS] APP_ID
```

Print the logs for an app.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |
| _--since DATE\_OR\_TIMEDELTA_ | Only return logs after a specific date \(including\). Use value of format '1d2h3m4s' to specify moment in past relatively to current time. |
| _--timestamps_ | Include timestamps on each line in the log output. |



### ls

Alias to list


#### Usage

```bash
apolo app ls [OPTIONS]
```

Alias to list

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-a, --all_ | Show apps in all states. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |
| _-s, --state \[queued &#124; progressing &#124; healthy &#124; degraded &#124; errored &#124; uninstalling &#124; uninstalled\]_ | Filter out apps by state \(multiple option\). |



### uninstall

Uninstall an app


#### Usage

```bash
apolo app uninstall [OPTIONS] APP_ID
```

Uninstall an app.

`APP`_ID: ID of the app to uninstall

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _-f, --force_ | Force uninstall the app. |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |


