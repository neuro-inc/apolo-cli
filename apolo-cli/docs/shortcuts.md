# Shortcuts
**Commands:**
| Usage | Description |
| :--- | :--- |
| [_apolo attach_](shortcuts.md#attach) | Attach terminal to a job |
| [_apolo cp_](shortcuts.md#cp) | Copy files and directories |
| [_apolo exec_](shortcuts.md#exec) | Execute command in a running job |
| [_apolo images_](shortcuts.md#images) | List images |
| [_apolo kill_](shortcuts.md#kill) | Kill job\(s\) |
| [_apolo login_](shortcuts.md#login) | Log into Apolo Platform |
| [_apolo logout_](shortcuts.md#logout) | Log out |
| [_apolo logs_](shortcuts.md#logs) | Print the logs for a job |
| [_apolo ls_](shortcuts.md#ls) | List directory contents |
| [_apolo mcp_](shortcuts.md#mcp) | Start MCP server for AI agent integration |
| [_apolo mkdir_](shortcuts.md#mkdir) | Make directories |
| [_apolo mv_](shortcuts.md#mv) | Move or rename files and directories |
| [_apolo port-forward_](shortcuts.md#port-forward) | Forward port\(s\) of a job |
| [_apolo ps_](shortcuts.md#ps) | List all jobs |
| [_apolo pull_](shortcuts.md#pull) | Pull an image from platform registry |
| [_apolo push_](shortcuts.md#push) | Push an image to platform registry |
| [_apolo rm_](shortcuts.md#rm) | Remove files or directories |
| [_apolo run_](shortcuts.md#run) | Run a job |
| [_apolo save_](shortcuts.md#save) | Save job's state to an image |
| [_apolo share_](shortcuts.md#share) | Shares resource with another user |
| [_apolo status_](shortcuts.md#status) | Display status of a job |
| [_apolo top_](shortcuts.md#top) | Display GPU/CPU/Memory usage |


### attach

Attach terminal to a job


#### Usage

```bash
apolo attach [OPTIONS] JOB
```

Attach terminal to a job

Attach local standard input, output, and error
streams to a running job.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--port-forward LOCAL\_PORT:REMOTE\_RORT_ | Forward port\(s\) of a running job to local port\(s\) \(use multiple times for forwarding several ports\) |



### cp

Copy files and directories


#### Usage

```bash
apolo cp [OPTIONS] [SOURCES]... [DESTINATION]
```

Copy files and directories.

Either `SOURCES` or `DESTINATION` should have
storage:// scheme.
If scheme is omitted, file:// scheme is assumed.

Use
/dev/stdin and /dev/stdout file names to copy a file from terminal
and print
the content of file on the storage to console.

Any number of --exclude and
--include options can be passed.  The
filters that appear later in the command
take precedence over filters
that appear earlier in the command.  If neither
--exclude nor
--include options are specified the default can be changed using
the
storage.cp-exclude configuration variable documented in
"apolo help user-
config".

#### Examples

```bash

# copy local files into remote storage root
$ apolo cp foo.txt bar/baz.dat storage:
$ apolo cp foo.txt bar/baz.dat -t storage:

# copy local directory `foo` into existing remote directory `bar`
$ apolo cp -r foo -t storage:bar

# copy the content of local directory `foo` into existing remote
# directory `bar`
$ apolo cp -r -T storage:foo storage:bar

# download remote file `foo.txt` into local file `/tmp/foo.txt` with
# explicit file:// scheme set
$ apolo cp storage:foo.txt file:///tmp/foo.txt
$ apolo cp -T storage:foo.txt file:///tmp/foo.txt
$ apolo cp storage:foo.txt file:///tmp
$ apolo cp storage:foo.txt -t file:///tmp

# download other project's remote file into the current directory
$ apolo cp storage:/{project}/foo.txt .

# download only files with extension `.out` into the current directory
$ apolo cp storage:results/*.out .
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--continue_ | Continue copying partially-copied files. |
| _--exclude-from-files FILES_ | A list of file names that contain patterns for exclusion files and directories. Used only for uploading. The default can be changed using the storage.cp-exclude-from-files configuration variable documented in "apolo help user-config" |
| _--exclude TEXT_ | Exclude files and directories that match the specified pattern. |
| _--include TEXT_ | Don't exclude files and directories that match the specified pattern. |
| _--glob / --no-glob_ | Expand glob patterns in SOURCES with explicit scheme.  _\[default: glob\]_ |
| _-T, --no-target-directory_ | Treat DESTINATION as a normal file. |
| _-p, --progress / -P, --no-progress_ | Show progress, on by default in TTY mode, off otherwise. |
| _-r, --recursive_ | Recursive copy, off by default |
| _-t, --target-directory DIRECTORY_ | Copy all SOURCES into DIRECTORY. |
| _-u, --update_ | Copy only when the SOURCE file is newer than the destination file or when the destination file is missing. |



### exec

Execute command in a running job


#### Usage

```bash
apolo exec [OPTIONS] JOB -- CMD...
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



### images

List images


#### Usage

```bash
apolo images [OPTIONS]
```

List images.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--all-orgs_ | Show images in all orgs. |
| _--all-projects_ | Show images in all projects. |
| _--cluster CLUSTER_ | Show images on a specified cluster \(the current cluster by default\). |
| _-l_ | List in long format. |
| _--full-uri_ | Output full image URI. |
| _-n, --name PATTERN_ | Filter out images by name regex. |
| _--org ORG_ | Filter out images by org \(multiple option, the current org by default\). |
| _--project PROJECT_ | Filter out images by project \(multiple option, the current project by default\). |



### kill

Kill job(s)


#### Usage

```bash
apolo kill [OPTIONS] JOBS...
```

Kill job(s).

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### login

Log into Apolo Platform


#### Usage

```bash
apolo login [OPTIONS] [URL]
```

Log into Apolo Platform.

`URL` is a platform entrypoint `URL`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### logout

Log out


#### Usage

```bash
apolo logout [OPTIONS]
```

Log out.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### logs

Print the logs for a job


#### Usage

```bash
apolo logs [OPTIONS] JOB
```

Print the logs for a job.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--since DATE\_OR\_TIMEDELTA_ | Only return logs after a specific date \(including\). Use value of format '1d2h3m4s' to specify moment in past relatively to current time. |
| _--timestamps_ | Include timestamps on each line in the log output. |



### ls

List directory contents


#### Usage

```bash
apolo ls [OPTIONS] [PATHS]...
```

List directory contents.

By default `PATH` is equal project's dir (storage:)

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-d, --directory_ | list directories themselves, not their contents. |
| _-l_ | use a long listing format. |
| _-h, --human-readable_ | with -l print human readable sizes \(e.g., 2K, 540M\). |
| _-a, --all_ | do not ignore entries starting with . |
| _--sort \[name &#124; size &#124; time\]_ | sort by given field, default is name. |



### mcp

Start MCP server for AI agent integration


#### Usage

```bash
apolo mcp [OPTIONS]
```

Start `MCP` server for AI agent integration.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### mkdir

Make directories


#### Usage

```bash
apolo mkdir [OPTIONS] PATHS...
```

Make directories.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-p, --parents_ | No error if existing, make parent directories as needed |



### mv

Move or rename files and directories


#### Usage

```bash
apolo mv [OPTIONS] [SOURCES]... [DESTINATION]
```

Move or rename files and directories.

`SOURCE` must contain path to the
file
or directory existing on the storage, and `DESTINATION` must contain
the full
path to the target file or directory.

#### Examples

```bash

# move and rename remote file
$ apolo mv storage:foo.txt storage:bar/baz.dat
$ apolo mv -T storage:foo.txt storage:bar/baz.dat

# move remote files into existing remote directory
$ apolo mv storage:foo.txt storage:bar/baz.dat storage:dst
$ apolo mv storage:foo.txt storage:bar/baz.dat -t storage:dst

# move the content of remote directory into other existing
# remote directory
$ apolo mv -T storage:foo storage:bar

# move remote file into other project's directory
$ apolo mv storage:foo.txt storage:/{project}/bar.dat

# move remote file from other project's directory
$ apolo mv storage:/{project}/foo.txt storage:bar.dat
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--glob / --no-glob_ | Expand glob patterns in SOURCES  _\[default: glob\]_ |
| _-T, --no-target-directory_ | Treat DESTINATION as a normal file |
| _-t, --target-directory DIRECTORY_ | Copy all SOURCES into DIRECTORY |



### port-forward

Forward port(s) of a job


#### Usage

```bash
apolo port-forward [OPTIONS] JOB LOCAL_PORT:REMOTE_RORT...
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



### ps

List all jobs


#### Usage

```bash
apolo ps [OPTIONS]
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



### pull

Pull an image from platform registry


#### Usage

```bash
apolo pull [OPTIONS] REMOTE_IMAGE [LOCAL_IMAGE]
```

Pull an image from platform registry.

Remote image name must be `URL` with
image:// scheme.
Image names can contain tag.

#### Examples

```bash

$ apolo pull image:myimage
$ apolo pull image:/other-project/alpine:shared
$ apolo pull image:/project/my-alpine:production alpine:from-registry
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### push

Push an image to platform registry


#### Usage

```bash
apolo push [OPTIONS] LOCAL_IMAGE [REMOTE_IMAGE]
```

Push an image to platform registry.

Remote image must be `URL` with image://
scheme.
Image names can contain tag. If tags not specified 'latest' will
be
used as value.

#### Examples

```bash

$ apolo push myimage
$ apolo push alpine:latest image:my-alpine:production
$ apolo push alpine image:/other-project/alpine:shared
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### rm

Remove files or directories


#### Usage

```bash
apolo rm [OPTIONS] PATHS...
```

Remove files or directories.

#### Examples

```bash

$ apolo rm storage:foo/bar
$ apolo rm storage:/{project}/foo/bar
$ apolo rm storage://{cluster}/{project}/foo/bar
$ apolo rm --recursive storage:/{project}/foo/
$ apolo rm storage:foo/**/*.tmp
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--glob / --no-glob_ | Expand glob patterns in PATHS  _\[default: glob\]_ |
| _-p, --progress / -P, --no-progress_ | Show progress, on by default in TTY mode, off otherwise. |
| _-r, --recursive_ | remove directories and their contents recursively |



### run

Run a job


#### Usage

```bash
apolo run [OPTIONS] IMAGE [-- CMD...]
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
apolo save [OPTIONS] JOB IMAGE
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



### share

Shares resource with another user


#### Usage

```bash
apolo share [OPTIONS] URI USER {read|write|manage}
```

Shares resource with another user.

`URI` shared resource.

`USER` username to
share resource with.

`PERMISSION` sharing access right: read, write, or
manage.

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



### status

Display status of a job


#### Usage

```bash
apolo status [OPTIONS] JOB
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
apolo top [OPTIONS] [JOBS]...
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


