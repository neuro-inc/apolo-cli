# app-template

Application Templates operations

## Usage

```bash
apolo app-template [OPTIONS] COMMAND [ARGS]...
```

Application Templates operations.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_get_](app-template.md#get) | Generate payload for 'app install' with... |
| [_list_](app-template.md#list) | List available application templates |
| [_list-versions_](app-template.md#list-versions) | List app template versions |
| [_ls_](app-template.md#ls) | Alias to list |
| [_ls-versions_](app-template.md#ls-versions) | Alias to list-versions |


### get

Generate payload for 'app install' with...


#### Usage

```bash
apolo app-template get [OPTIONS] NAME
```

Generate payload for 'app install' with sample data.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _-f, --file TEXT_ | Save output to a file instead of displaying it. |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _-o, --output TEXT_ | Output format \(yaml, json\). Default is yaml. |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |
| _-V, --version TEXT_ | Specify the version of the app template \(latest if not specified\). |



### list

List available application templates


#### Usage

```bash
apolo app-template list [OPTIONS]
```

List available application templates.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### list-versions

List app template versions


#### Usage

```bash
apolo app-template list-versions [OPTIONS] NAME
```

List app template versions.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### ls

Alias to list


#### Usage

```bash
apolo app-template ls [OPTIONS]
```

Alias to list

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### ls-versions

Alias to list-versions


#### Usage

```bash
apolo app-template ls-versions [OPTIONS] NAME
```

Alias to list-versions

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |


