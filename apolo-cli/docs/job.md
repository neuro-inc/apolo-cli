# job

Job operations

## Usage

```bash
apolo job [OPTIONS] COMMAND [ARGS]...
```

Job operations.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_attach_](job.md#attach) | Attach terminal to a job |
| [_browse_](job.md#browse) | Opens a job's URL in a web browser |
| [_bump-life-span_](job.md#bump-life-span) | Increase job life span |
| [_exec_](job.md#exec) | Execute command in a running job |
| [_generate-run_](job.md#generate-run) | Generate command that will rerun given job |
| [_kill_](job.md#kill) | Kill job\(s\) |
| [_logs_](job.md#logs) | Print the logs for a job |
| [_ls_](job.md#ls) | List all jobs |
| [_port-forward_](job.md#port-forward) | Forward port\(s\) of a job |
| [_run_](job.md#run) | Run a job |
| [_save_](job.md#save) | Save job's state to an image |
| [_status_](job.md#status) | Display status of a job |
| [_top_](job.md#top) | Display GPU/CPU/Memory usage |


### attach

Attach terminal to a job


#### Usage

```bash
apolo job attach [OPTIONS] JOB
```

Attach terminal to a job

Attach local standard input, output, and error
streams to a running job.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--port-forward LOCAL\_PORT:REMOTE\_RORT_ | Forward port\(s\) of a running job to local port\(s\) \(use multiple times for forwarding several ports\) |



### browse

Opens a job's URL in a web browser


#### Usage

```bash
apolo job browse [OPTIONS] JOB
```

Opens a job's `URL` in a web browser.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### bump-life-span

Increase job life span


#### Usage

```bash
apolo job bump-life-span [OPTIONS] JOB TIMEDELTA
```

Increase job life span

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### exec

Execute command in a running job


#### Usage

```bash
apolo job exec [OPTIONS] JOB -- CMD...
```

Execute command in a running job.

#### Examples

```bash

# Provides a shell to the container:
$ apolo exec my-job -- /bin/bash

# Executes a single command in the container and returns the control:
$ apolo exec --no-tty my-job -- ls -l
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-t, --tty / -T, --no-tty_ | Allocate a TTY, can be useful for interactive jobs. By default is on if the command is executed from a terminal, non-tty mode is used if executed from a script. |



### generate-run

Generate command that will rerun given job


#### Usage

```bash
apolo job generate-run [OPTIONS] JOB
```

Generate command that will rerun given job.

#### Examples

```bash

# You can use the following to directly re-execute it:
$ eval $(apolo job generate-run-command <job-id>)
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### kill

Kill job(s)


#### Usage

```bash
apolo job kill [OPTIONS] JOBS...
```

Kill job(s).

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### logs

Print the logs for a job


#### Usage

```bash
apolo job logs [OPTIONS] JOB
```

Print the logs for a job.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--since DATE\_OR\_TIMEDELTA_ | Only return logs after a specific date \(including\). Use value of format '1d2h3m4s' to specify moment in past relatively to current time. |
| _--timestamps_ | Include timestamps on each line in the log output. |



### ls

List all jobs


#### Usage

```bash
apolo job ls [OPTIONS]
```

List all jobs.

#### Examples

```bash

$ apolo ps -a
$ apolo ps -a --owner=user-1 --owner=user-2
$ apolo ps --name my-experiments-v1 -s failed -s succeeded
$ apolo ps --description=my favourite job
$ apolo ps -s failed -s succeeded -q
$ apolo ps -t tag1 -t tag2
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-a, --all_ | Show all jobs regardless the status. |
| _--all-orgs_ | Show jobs in all orgs. |
| _--all-projects_ | Show jobs in all projects. |
| _--cluster CLUSTER_ | Show jobs on a specified cluster \(the current cluster by default\). |
| _-d, --description DESCRIPTION_ | Filter out jobs by description \(exact match\). |
| _--distinct_ | Show only first job if names are same. |
| _--format COLUMNS_ | Output table format, see "apolo help ps-format" for more info about the format specification. The default can be changed using the job.ps-format configuration variable documented in "apolo help user-config" |
| _--full-uri_ | Output full image URI. |
| _-n, --name NAME_ | Filter out jobs by name. |
| _--org ORG_ | Filter out jobs by org name \(multiple option, the current org by default\). |
| _-o, --owner TEXT_ | Filter out jobs by owner \(multiple option\). Supports `ME` option to filter by the current user. |
| _-p, --project PROJECT_ | Filter out jobs by project name \(multiple option, the current project by default\). |
| _--recent-first / --recent-last_ | Show newer jobs first or last |
| _--since DATE\_OR\_TIMEDELTA_ | Show jobs created after a specific date \(including\). Use value of format '1d2h3m4s' to specify moment in past relatively to current time. |
| _-s, --status \[pending &#124; suspended &#124; running &#124; succeeded &#124; failed &#124; cancelled\]_ | Filter out jobs by status \(multiple option\). |
| _-t, --tag TAG_ | Filter out jobs by tag \(multiple option\) |
| _--until DATE\_OR\_TIMEDELTA_ | Show jobs created before a specific date \(including\). Use value of format '1d2h3m4s' to specify moment in past relatively to current time. |
| _-w, --wide_ | Do not cut long lines for terminal width. |



### port-forward

Forward port(s) of a job


#### Usage

```bash
apolo job port-forward [OPTIONS] JOB LOCAL_PORT:REMOTE_RORT...
```

Forward port(s) of a job.

Forwards port(s) of a running job to local port(s).

#### Examples

```bash

# Forward local port 2080 to port 80 of job's container.
# You can use http://localhost:2080 in browser to access job's served http
$ apolo job port-forward my-fastai-job 2080:80

# Forward local port 2222 to job's port 22
# Then copy all data from container's folder '/data' to current folder
# (please run second command in other terminal)
$ apolo job port-forward my-job-with-ssh-server 2222:22
$ rsync -avxzhe ssh -p 2222 root@localhost:/data .

# Forward few ports at once
$ apolo job port-forward my-job 2080:80 2222:22 2000:100
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### run

Run a job


#### Usage

```bash
apolo job run [OPTIONS] IMAGE [-- CMD...]
```

Run a job

`IMAGE` docker image name to run in a job.

`CMD` list will be
passed as arguments to the executed job's image.

#### Examples

```bash

# Starts a container pytorch/pytorch:latest on a machine with smaller GPU resources
# (see exact values in `apolo config show`) and with two volumes mounted:
#   storage:/<home-directory>   --> /var/storage/home (in read-write mode),
#   storage:/neuromation/public --> /var/storage/neuromation (in read-only mode).
$ apolo run --preset=gpu-small --volume=storage::/var/storage/home:rw \
$ --volume=storage:/neuromation/public:/var/storage/home:ro pytorch/pytorch:latest

# Starts a container using the custom image my-ubuntu:latest stored in apolo
# registry, run /script.sh and pass arg1 and arg2 as its arguments:
$ apolo run -s cpu-small --entrypoint=/script.sh image:my-ubuntu:latest -- arg1 arg2
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--browse_ | Open a job's URL in a web browser |
| _--cluster CLUSTER_ | Run job in a specified cluster |
| _-d, --description DESC_ | Optional job description in free format |
| _--detach_ | Don't attach to job logs and don't wait for exit code |
| _--energy-schedule NAME_ | Run job only within a selected energy schedule. Selected preset should have scheduler enabled. |
| _--entrypoint TEXT_ | Executable entrypoint in the container \(note that it overwrites `ENTRYPOINT` and `CMD` instructions of the docker image\) |
| _-e, --env VAR=VAL_ | Set environment variable in container. Use multiple options to define more than one variable. See `apolo help secrets` for information about passing secrets as environment variables. |
| _--env-file PATH_ | File with environment variables to pass |
| _-x, --extshm / -X, --no-extshm_ | Request extended '/dev/shm' space  _\[default: x\]_ |
| _--http-auth / --no-http-auth_ | Enable HTTP authentication for forwarded HTTP port  _\[default: True\]_ |
| _--http-port PORT_ | Enable HTTP port forwarding to container  _\[default: 80\]_ |
| _--life-span TIMEDELTA_ | Optional job run-time limit in the format '1d2h3m4s' \(some parts may be missing\). Set '0' to disable. Default value '1d' can be changed in the user config. |
| _-n, --name NAME_ | Optional job name |
| _--org ORG_ | Run job in a specified org |
| _--pass-config / --no-pass-config_ | Upload apolo config to the job  _\[default: no-pass-config\]_ |
| _--port-forward LOCAL\_PORT:REMOTE\_RORT_ | Forward port\(s\) of a running job to local port\(s\) \(use multiple times for forwarding several ports\) |
| _-s, --preset PRESET_ | Predefined resource configuration \(to see available values, run `apolo config show`\) |
| _--priority \[low &#124; normal &#124; high\]_ | Priority used to specify job's start order. Jobs with higher priority will start before ones with lower priority. Priority should be supported by cluster. |
| _--privileged_ | Run job in privileged mode, if it is supported by cluster. |
| _-p, --project PROJECT_ | Run job in a specified project. |
| _--restart \[never &#124; on-failure &#124; always\]_ | Restart policy to apply when a job exits  _\[default: never\]_ |
| _--schedule-timeout TIMEDELTA_ | Optional job schedule timeout in the format '3m4s' \(some parts may be missing\). |
| _--share USER_ | Share job write permissions to user or role. |
| _--tag TAG_ | Optional job tag, multiple values allowed |
| _-t, --tty / -T, --no-tty_ | Allocate a TTY, can be useful for interactive jobs. By default is on if the command is executed from a terminal, non-tty mode is used if executed from a script. |
| _-v, --volume MOUNT_ | Mounts directory from vault into container. Use multiple options to mount more than one volume. See `apolo help secrets` for information about passing secrets as mounted files. |
| _--wait-for-seat / --no-wait-for-seat_ | Wait for total running jobs quota  _\[default: no-wait-for-seat\]_ |
| _--wait-start / --no-wait-start_ | Wait for a job start or failure  _\[default: wait-start\]_ |
| _-w, --workdir TEXT_ | Working directory inside the container |



### save

Save job's state to an image


#### Usage

```bash
apolo job save [OPTIONS] JOB IMAGE
```

Save job's state to an image.

#### Examples

```bash
$ apolo job save job-id image:ubuntu-patched
$ apolo job save my-favourite-job image:ubuntu-patched:v1
$ apolo job save my-favourite-job image://bob/ubuntu-patched
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### status

Display status of a job


#### Usage

```bash
apolo job status [OPTIONS] JOB
```

Display status of a job.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--full-uri_ | Output full URI. |



### top

Display GPU/CPU/Memory usage


#### Usage

```bash
apolo job top [OPTIONS] [JOBS]...
```

Display `GPU`/`CPU`/Memory usage.

#### Examples

```bash

$ apolo top
$ apolo top job-1 job-2
$ apolo top --owner=user-1 --owner=user-2
$ apolo top --name my-experiments-v1
$ apolo top -t tag1 -t tag2
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Show jobs on a specified cluster \(the current cluster by default\). |
| _-d, --description DESCRIPTION_ | Filter out jobs by description \(exact match\). |
| _--format COLUMNS_ | Output table format, see "apolo help top-format" for more info about the format specification. The default can be changed using the job.top-format configuration variable documented in "apolo help user-config" |
| _--full-uri_ | Output full image URI. |
| _-n, --name NAME_ | Filter out jobs by name. |
| _-o, --owner TEXT_ | Filter out jobs by owner \(multiple option\). Supports `ME` option to filter by the current user. Specify `ALL` to show jobs of all users. |
| _-p, --project PROJECT_ | Filter out jobs by project name \(multiple option\). |
| _--since DATE\_OR\_TIMEDELTA_ | Show jobs created after a specific date \(including\). Use value of format '1d2h3m4s' to specify moment in past relatively to current time. |
| _--sort COLUMNS_ | Sort rows by specified column. Add "-" prefix to revert the sorting order. Multiple columns can be specified \(comma separated\).  _\[default: cpu\]_ |
| _-t, --tag TAG_ | Filter out jobs by tag \(multiple option\) |
| _--timeout FLOAT_ | Maximum allowed time for executing the command, 0 for no timeout  _\[default: 0\]_ |
| _--until DATE\_OR\_TIMEDELTA_ | Show jobs created before a specific date \(including\). Use value of format '1d2h3m4s' to specify moment in past relatively to current time. |


