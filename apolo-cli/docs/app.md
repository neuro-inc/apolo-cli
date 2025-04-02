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
| [_install_](app.md#install) | Install an app from a YAML file |
| [_ls_](app.md#ls) | List apps |
| [_uninstall_](app.md#uninstall) | Uninstall an app |


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



### ls

List apps


#### Usage

```bash
apolo app ls [OPTIONS]
```

List apps.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



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
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |


