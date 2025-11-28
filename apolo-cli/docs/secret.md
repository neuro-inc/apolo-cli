# secret

Operations with secrets

## Usage

```bash
apolo secret [OPTIONS] COMMAND [ARGS]...
```

Operations with secrets.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_add_](secret.md#add) | Add secret KEY with data VALUE |
| [_ls_](secret.md#ls) | List secrets |
| [_rm_](secret.md#rm) | Remove secret KEY |


### add

Add secret KEY with data VALUE


#### Usage

```bash
apolo secret add [OPTIONS] KEY VALUE
```

Add secret `KEY` with data `VALUE`.

If `VALUE` starts with @ it points to a
file with secrets content.

#### Examples

```bash

$ apolo secret add KEY_NAME VALUE
$ apolo secret add KEY_NAME @path/to/file.txt
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Perform on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### ls

List secrets


#### Usage

```bash
apolo secret ls [OPTIONS]
```

List secrets.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--all-orgs_ | Show secrets in all orgs. |
| _--all-projects_ | Show secrets in all projects. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--full-uri_ | Output full secret URI. |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### rm

Remove secret KEY


#### Usage

```bash
apolo secret rm [OPTIONS] KEY
```

Remove secret `KEY`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Perform on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |


