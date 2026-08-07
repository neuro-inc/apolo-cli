# disk

Operations with disks

## Usage

```bash
apolo disk [OPTIONS] COMMAND [ARGS]...
```

Operations with disks.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_create_](disk.md#create) | Create a disk |
| [_get_](disk.md#get) | Get disk DISK\_ID |
| [_ls_](disk.md#ls) | List disks |
| [_rm_](disk.md#rm) | Remove disk DISK\_ID |


### create

Create a disk


#### Usage

```bash
apolo disk create [OPTIONS] STORAGE
```

Create a disk

Create a disk with at least storage amount `STORAGE`.

To
specify the amount, you can use the following suffixes: "k`KMGTPEZY`"
To use
decimal quantities, append "b" or "B". For example:
- 1K or 1k is `1024` bytes
- 1Kb or `1KB` is `1000` bytes
- `20G` is 20 * 2 ^ 30 bytes
- `20G`b or `20GB`
is 20.`000`.`000`.`000` bytes

Note that server can have big granularity (for
example, 1G)
so it will possibly round-up the amount you requested.

#### Examples

```bash

$ apolo disk create 10G
$ apolo disk create 500M
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Perform in a specified cluster \(the current cluster by default\). |
| _--name NAME_ | Optional disk name |
| _--org ORG_ | Perform in a specified org \(the current org by default\). |
| _--project PROJECT_ | Create disk in a specified project \(the current project by default\). |
| _--timeout-unused TIMEDELTA_ | Optional disk lifetime limit after last usage in the format '1d2h3m4s' \(some parts may be missing\). Set '0' to disable. Default value '1d' can be changed in the user config. |



### get

Get disk DISK_ID


#### Usage

```bash
apolo disk get [OPTIONS] DISK
```

Get disk `DISK_ID`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--full-uri_ | Output full disk URI. |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### ls

List disks


#### Usage

```bash
apolo disk ls [OPTIONS]
```

List disks.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--all-orgs_ | Show disks in all orgs. |
| _--all-projects_ | Show disks in all projects. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--full-uri_ | Output full disk URI. |
| _--long-format_ | Output all info about disk. |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### rm

Remove disk DISK_ID


#### Usage

```bash
apolo disk rm [OPTIONS] DISKS...
```

Remove disk `DISK_ID`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Perform on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Perform on a specified org \(the current org by default\). |
| _--project PROJECT_ | Perform on a specified project \(the current project by default\). |


