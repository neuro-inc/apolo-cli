

# Table of Contents
* [apolo](#apolo)
	* [apolo acl](#apolo-acl)
		* [apolo acl add-role](#apolo-acl-add-role)
		* [apolo acl grant](#apolo-acl-grant)
		* [apolo acl list-roles](#apolo-acl-list-roles)
		* [apolo acl ls](#apolo-acl-ls)
		* [apolo acl remove-role](#apolo-acl-remove-role)
		* [apolo acl revoke](#apolo-acl-revoke)
	* [apolo admin](#apolo-admin)
		* [apolo admin add-cluster](#apolo-admin-add-cluster)
		* [apolo admin add-cluster-user](#apolo-admin-add-cluster-user)
		* [apolo admin add-org](#apolo-admin-add-org)
		* [apolo admin add-org-cluster](#apolo-admin-add-org-cluster)
		* [apolo admin add-org-credits](#apolo-admin-add-org-credits)
		* [apolo admin add-org-user](#apolo-admin-add-org-user)
		* [apolo admin add-project](#apolo-admin-add-project)
		* [apolo admin add-project-user](#apolo-admin-add-project-user)
		* [apolo admin add-resource-preset](#apolo-admin-add-resource-preset)
		* [apolo admin add-user-credits](#apolo-admin-add-user-credits)
		* [apolo admin generate-cluster-config](#apolo-admin-generate-cluster-config)
		* [apolo admin get-cluster-orgs](#apolo-admin-get-cluster-orgs)
		* [apolo admin get-cluster-users](#apolo-admin-get-cluster-users)
		* [apolo admin get-clusters](#apolo-admin-get-clusters)
		* [apolo admin get-org-cluster-quota](#apolo-admin-get-org-cluster-quota)
		* [apolo admin get-org-users](#apolo-admin-get-org-users)
		* [apolo admin get-orgs](#apolo-admin-get-orgs)
		* [apolo admin get-project-users](#apolo-admin-get-project-users)
		* [apolo admin get-projects](#apolo-admin-get-projects)
		* [apolo admin get-user-quota](#apolo-admin-get-user-quota)
		* [apolo admin remove-cluster](#apolo-admin-remove-cluster)
		* [apolo admin remove-cluster-user](#apolo-admin-remove-cluster-user)
		* [apolo admin remove-org](#apolo-admin-remove-org)
		* [apolo admin remove-org-cluster](#apolo-admin-remove-org-cluster)
		* [apolo admin remove-org-user](#apolo-admin-remove-org-user)
		* [apolo admin remove-project](#apolo-admin-remove-project)
		* [apolo admin remove-project-user](#apolo-admin-remove-project-user)
		* [apolo admin remove-resource-preset](#apolo-admin-remove-resource-preset)
		* [apolo admin set-org-cluster-defaults](#apolo-admin-set-org-cluster-defaults)
		* [apolo admin set-org-cluster-quota](#apolo-admin-set-org-cluster-quota)
		* [apolo admin set-org-credits](#apolo-admin-set-org-credits)
		* [apolo admin set-org-defaults](#apolo-admin-set-org-defaults)
		* [apolo admin set-user-credits](#apolo-admin-set-user-credits)
		* [apolo admin set-user-quota](#apolo-admin-set-user-quota)
		* [apolo admin show-cluster-options](#apolo-admin-show-cluster-options)
		* [apolo admin update-cluster](#apolo-admin-update-cluster)
		* [apolo admin update-cluster-user](#apolo-admin-update-cluster-user)
		* [apolo admin update-node-pool](#apolo-admin-update-node-pool)
		* [apolo admin update-org-cluster](#apolo-admin-update-org-cluster)
		* [apolo admin update-project](#apolo-admin-update-project)
		* [apolo admin update-project-user](#apolo-admin-update-project-user)
		* [apolo admin update-resource-preset](#apolo-admin-update-resource-preset)
	* [apolo app](#apolo-app)
		* [apolo app list](#apolo-app-list)
	* [apolo blob](#apolo-blob)
		* [apolo blob cp](#apolo-blob-cp)
		* [apolo blob du](#apolo-blob-du)
		* [apolo blob glob](#apolo-blob-glob)
		* [apolo blob importbucket](#apolo-blob-importbucket)
		* [apolo blob ls](#apolo-blob-ls)
		* [apolo blob lsbucket](#apolo-blob-lsbucket)
		* [apolo blob lscredentials](#apolo-blob-lscredentials)
		* [apolo blob mkbucket](#apolo-blob-mkbucket)
		* [apolo blob mkcredentials](#apolo-blob-mkcredentials)
		* [apolo blob rm](#apolo-blob-rm)
		* [apolo blob rmbucket](#apolo-blob-rmbucket)
		* [apolo blob rmcredentials](#apolo-blob-rmcredentials)
		* [apolo blob set-bucket-publicity](#apolo-blob-set-bucket-publicity)
		* [apolo blob sign-url](#apolo-blob-sign-url)
		* [apolo blob statbucket](#apolo-blob-statbucket)
		* [apolo blob statcredentials](#apolo-blob-statcredentials)
	* [apolo completion](#apolo-completion)
		* [apolo completion generate](#apolo-completion-generate)
		* [apolo completion patch](#apolo-completion-patch)
	* [apolo config](#apolo-config)
		* [apolo config aliases](#apolo-config-aliases)
		* [apolo config docker](#apolo-config-docker)
		* [apolo config get-clusters](#apolo-config-get-clusters)
		* [apolo config login](#apolo-config-login)
		* [apolo config login-headless](#apolo-config-login-headless)
		* [apolo config login-with-token](#apolo-config-login-with-token)
		* [apolo config logout](#apolo-config-logout)
		* [apolo config show](#apolo-config-show)
		* [apolo config show-token](#apolo-config-show-token)
		* [apolo config switch-cluster](#apolo-config-switch-cluster)
		* [apolo config switch-org](#apolo-config-switch-org)
		* [apolo config switch-project](#apolo-config-switch-project)
	* [apolo disk](#apolo-disk)
		* [apolo disk create](#apolo-disk-create)
		* [apolo disk get](#apolo-disk-get)
		* [apolo disk ls](#apolo-disk-ls)
		* [apolo disk rm](#apolo-disk-rm)
	* [apolo image](#apolo-image)
		* [apolo image digest](#apolo-image-digest)
		* [apolo image ls](#apolo-image-ls)
		* [apolo image pull](#apolo-image-pull)
		* [apolo image push](#apolo-image-push)
		* [apolo image rm](#apolo-image-rm)
		* [apolo image size](#apolo-image-size)
		* [apolo image tags](#apolo-image-tags)
	* [apolo job](#apolo-job)
		* [apolo job attach](#apolo-job-attach)
		* [apolo job browse](#apolo-job-browse)
		* [apolo job bump-life-span](#apolo-job-bump-life-span)
		* [apolo job exec](#apolo-job-exec)
		* [apolo job generate-run-command](#apolo-job-generate-run-command)
		* [apolo job kill](#apolo-job-kill)
		* [apolo job logs](#apolo-job-logs)
		* [apolo job ls](#apolo-job-ls)
		* [apolo job port-forward](#apolo-job-port-forward)
		* [apolo job run](#apolo-job-run)
		* [apolo job save](#apolo-job-save)
		* [apolo job status](#apolo-job-status)
		* [apolo job top](#apolo-job-top)
	* [apolo secret](#apolo-secret)
		* [apolo secret add](#apolo-secret-add)
		* [apolo secret ls](#apolo-secret-ls)
		* [apolo secret rm](#apolo-secret-rm)
	* [apolo service-account](#apolo-service-account)
		* [apolo service-account create](#apolo-service-account-create)
		* [apolo service-account get](#apolo-service-account-get)
		* [apolo service-account ls](#apolo-service-account-ls)
		* [apolo service-account rm](#apolo-service-account-rm)
	* [apolo storage](#apolo-storage)
		* [apolo storage cp](#apolo-storage-cp)
		* [apolo storage df](#apolo-storage-df)
		* [apolo storage glob](#apolo-storage-glob)
		* [apolo storage ls](#apolo-storage-ls)
		* [apolo storage mkdir](#apolo-storage-mkdir)
		* [apolo storage mv](#apolo-storage-mv)
		* [apolo storage rm](#apolo-storage-rm)
		* [apolo storage tree](#apolo-storage-tree)
	* [apolo attach](#apolo-attach)
	* [apolo cp](#apolo-cp)
	* [apolo exec](#apolo-exec)
	* [apolo help](#apolo-help)
	* [apolo images](#apolo-images)
	* [apolo kill](#apolo-kill)
	* [apolo login](#apolo-login)
	* [apolo logout](#apolo-logout)
	* [apolo logs](#apolo-logs)
	* [apolo ls](#apolo-ls)
	* [apolo mkdir](#apolo-mkdir)
	* [apolo mv](#apolo-mv)
	* [apolo port-forward](#apolo-port-forward)
	* [apolo ps](#apolo-ps)
	* [apolo pull](#apolo-pull)
	* [apolo push](#apolo-push)
	* [apolo rm](#apolo-rm)
	* [apolo run](#apolo-run)
	* [apolo save](#apolo-save)
	* [apolo share](#apolo-share)
	* [apolo status](#apolo-status)
	* [apolo top](#apolo-top)

# apolo

**Usage:**

```bash
apolo [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--color \[yes &#124; no &#124; auto]_|Color mode.|
|_\--config-path PATH_|Path to config directory.|
|_\--disable-pypi-version-check_|Don't periodically check PyPI to determine whether a new version of Apolo Platform CLI is available for download.  \[env var: NEURO\_CLI_DISABLE_PYPI_VERSION_CHECK]|
|_\--hide-token / --no-hide-token_|Prevent user's token sent in HTTP headers from being printed out to stderr during HTTP tracing. Can be used only together with option '--trace'. On by default.|
|_\--iso-datetime-format / --no-iso-datetime-format_|Use ISO 8601 format for printing date and time|
|_\--network-timeout FLOAT_|Network read timeout, seconds.|
|_\--neuromation-config PATH_|Path to config directory.|
|_\-q, --quiet_|Give less output. Option is additive, and can be used up to 2 times.|
|_\--show-traceback_|Show python traceback on error, useful for debugging the tool.|
|_\--skip-stats / --no-skip-stats_|Skip sending usage statistics to apolo servers. Note: the statistics has no sensitive data, e.g. file, job, image, or user names, executed command lines, environment variables, etc.|
|_--trace_|Trace sent HTTP requests and received replies to stderr.|
|_\-v, --verbose_|Give more output. Option is additive, and can be used up to 2 times.|
|_--version_|Show the version and exit.|


**Command Groups:**

|Usage|Description|
|---|---|
| _[apolo acl](#apolo-acl)_| Access Control List management |
| _[apolo admin](#apolo-admin)_| Cluster administration commands |
| _[apolo app](#apolo-app)_| Operations with applications |
| _[apolo blob](#apolo-blob)_| Blob storage operations |
| _[apolo completion](#apolo-completion)_| Output shell completion code |
| _[apolo config](#apolo-config)_| Client configuration |
| _[apolo disk](#apolo-disk)_| Operations with disks |
| _[apolo image](#apolo-image)_| Container image operations |
| _[apolo job](#apolo-job)_| Job operations |
| _[apolo secret](#apolo-secret)_| Operations with secrets |
| _[apolo service-account](#apolo-service-account)_| Operations with service accounts |
| _[apolo storage](#apolo-storage)_| Storage operations |


**Commands:**

|Usage|Description|
|---|---|
| _[apolo attach](#apolo-attach)_| Attach terminal to a job |
| _[apolo cp](#apolo-cp)_| Copy files and directories |
| _[apolo exec](#apolo-exec)_| Execute command in a running job |
| _[apolo help](#apolo-help)_| Get help on a command |
| _[apolo images](#apolo-images)_| List images |
| _[apolo kill](#apolo-kill)_| Kill job\(s) |
| _[apolo login](#apolo-login)_| Log into Apolo Platform |
| _[apolo logout](#apolo-logout)_| Log out |
| _[apolo logs](#apolo-logs)_| Print the logs for a job |
| _[apolo ls](#apolo-ls)_| List directory contents |
| _[apolo mkdir](#apolo-mkdir)_| Make directories |
| _[apolo mv](#apolo-mv)_| Move or rename files and directories |
| _[apolo port-forward](#apolo-port-forward)_| Forward port\(s) of a job |
| _[apolo ps](#apolo-ps)_| List all jobs |
| _[apolo pull](#apolo-pull)_| Pull an image from platform registry |
| _[apolo push](#apolo-push)_| Push an image to platform registry |
| _[apolo rm](#apolo-rm)_| Remove files or directories |
| _[apolo run](#apolo-run)_| Run a job |
| _[apolo save](#apolo-save)_| Save job's state to an image |
| _[apolo share](#apolo-share)_| Shares resource with another user |
| _[apolo status](#apolo-status)_| Display status of a job |
| _[apolo top](#apolo-top)_| Display GPU/CPU/Memory usage |




## apolo acl

Access Control List management.

**Usage:**

```bash
apolo acl [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo acl add-role](#apolo-acl-add-role)_| Add new role |
| _[apolo acl grant](#apolo-acl-grant)_| Shares resource with another user |
| _[apolo acl list-roles](#apolo-acl-list-roles)_| List roles |
| _[apolo acl ls](#apolo-acl-ls)_| List shared resources |
| _[apolo acl remove-role](#apolo-acl-remove-role)_| Remove existing role |
| _[apolo acl revoke](#apolo-acl-revoke)_| Revoke user access from another user |




### apolo acl add-role

Add new role.<br/>

**Usage:**

```bash
apolo acl add-role [OPTIONS] ROLE_NAME
```

**Examples:**

```bash

apolo acl add-role mycompany/subdivision

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo acl grant

Shares resource with another user.<br/><br/>URI shared resource.<br/><br/>USER username to share resource with.<br/><br/>PERMISSION sharing access right: read, write, or manage.<br/>

**Usage:**

```bash
apolo acl grant [OPTIONS] URI USER {read|write|manage}
```

**Examples:**

```bash

apolo acl grant storage:///sample_data/ alice manage
apolo acl grant image:resnet50 bob read
apolo acl grant job:///my_job_id alice write

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo acl list-roles

List roles.<br/>

**Usage:**

```bash
apolo acl list-roles [OPTIONS]
```

**Examples:**

```bash

apolo acl list-roles
apolo acl list-roles username/projects

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_-u TEXT_|Fetch roles of specified user or role.|




### apolo acl ls

List shared resources.<br/><br/>The command displays a list of resources shared BY current user \(default).<br/><br/>To display a list of resources shared WITH current user apply --shared option.<br/>

**Usage:**

```bash
apolo acl ls [OPTIONS] [URI]
```

**Examples:**

```bash

apolo acl list
apolo acl list storage://
apolo acl list --shared
apolo acl list --shared image://

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--full-uri_|Output full URI.|
|_--shared_|Output the resources shared by the user.|
|_-u TEXT_|Use specified user or role.|




### apolo acl remove-role

Remove existing role.<br/>

**Usage:**

```bash
apolo acl remove-role [OPTIONS] ROLE_NAME
```

**Examples:**

```bash

apolo acl remove-role mycompany/subdivision

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo acl revoke

Revoke user access from another user.<br/><br/>URI previously shared resource to revoke.<br/><br/>USER to revoke URI resource from.<br/>

**Usage:**

```bash
apolo acl revoke [OPTIONS] URI USER
```

**Examples:**

```bash

apolo acl revoke storage:///sample_data/ alice
apolo acl revoke image:resnet50 bob
apolo acl revoke job:///my_job_id alice

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo admin

Cluster administration commands.

**Usage:**

```bash
apolo admin [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo admin add-cluster](#apolo-admin-add-cluster)_| Create a new cluster |
| _[apolo admin add\-cluster-user](#apolo-admin-add-cluster-user)_| Add user access to a specified cluster |
| _[apolo admin add-org](#apolo-admin-add-org)_| Create a new org |
| _[apolo admin add\-org-cluster](#apolo-admin-add-org-cluster)_| Add org access to specified cluster |
| _[apolo admin add\-org-credits](#apolo-admin-add-org-credits)_| Add given values to org balance |
| _[apolo admin add\-org-user](#apolo-admin-add-org-user)_| Add user access to specified org |
| _[apolo admin add-project](#apolo-admin-add-project)_| Add new project to specified cluster |
| _[apolo admin add\-project-user](#apolo-admin-add-project-user)_| Add user access to specified project |
| _[apolo admin add\-resource-preset](#apolo-admin-add-resource-preset)_| Add new resource preset |
| _[apolo admin add\-user-credits](#apolo-admin-add-user-credits)_| Add given values to user credits |
| _[apolo admin generate\-cluster-config](#apolo-admin-generate-cluster-config)_| Create a cluster configuration file |
| _[apolo admin get\-cluster-orgs](#apolo-admin-get-cluster-orgs)_| Print the list of all orgs in the cluster |
| _[apolo admin get\-cluster-users](#apolo-admin-get-cluster-users)_| List users in specified cluster |
| _[apolo admin get-clusters](#apolo-admin-get-clusters)_| Print the list of available clusters |
| _[apolo admin get\-org-cluster-quota](#apolo-admin-get-org-cluster-quota)_| Get info about org quota in given cluster |
| _[apolo admin get\-org-users](#apolo-admin-get-org-users)_| List users in specified org |
| _[apolo admin get-orgs](#apolo-admin-get-orgs)_| Print the list of available orgs |
| _[apolo admin get\-project-users](#apolo-admin-get-project-users)_| List users in specified project |
| _[apolo admin get-projects](#apolo-admin-get-projects)_| Print the list of all projects in the cluster |
| _[apolo admin get\-user-quota](#apolo-admin-get-user-quota)_| Get info about user quota in given cluster |
| _[apolo admin remove-cluster](#apolo-admin-remove-cluster)_| Drop a cluster |
| _[apolo admin remove\-cluster-user](#apolo-admin-remove-cluster-user)_| Remove user access from the cluster |
| _[apolo admin remove-org](#apolo-admin-remove-org)_| Drop an org |
| _[apolo admin remove\-org-cluster](#apolo-admin-remove-org-cluster)_| Drop an org cluster |
| _[apolo admin remove\-org-user](#apolo-admin-remove-org-user)_| Remove user access from the org |
| _[apolo admin remove-project](#apolo-admin-remove-project)_| Drop a project |
| _[apolo admin remove\-project-user](#apolo-admin-remove-project-user)_| Remove user access from the project |
| _[apolo admin remove\-resource-preset](#apolo-admin-remove-resource-preset)_| Remove resource preset |
| _[apolo admin set\-org-cluster-defaults](#apolo-admin-set-org-cluster-defaults)_| Set org cluster defaults to given value |
| _[apolo admin set\-org-cluster-quota](#apolo-admin-set-org-cluster-quota)_| Set org cluster quota to given values |
| _[apolo admin set\-org-credits](#apolo-admin-set-org-credits)_| Set org credits to given value |
| _[apolo admin set\-org-defaults](#apolo-admin-set-org-defaults)_| Set org defaults to a given value |
| _[apolo admin set\-user-credits](#apolo-admin-set-user-credits)_| Set user credits to given value |
| _[apolo admin set\-user-quota](#apolo-admin-set-user-quota)_| Set user quota to given values |
| _[apolo admin show\-cluster-options](#apolo-admin-show-cluster-options)_| Show available cluster options |
| _[apolo admin update-cluster](#apolo-admin-update-cluster)_| Update a cluster |
| _[apolo admin update\-cluster-user](#apolo-admin-update-cluster-user)_|  |
| _[apolo admin update\-node-pool](#apolo-admin-update-node-pool)_| Update cluster node pool |
| _[apolo admin update\-org-cluster](#apolo-admin-update-org-cluster)_| Update org cluster quotas |
| _[apolo admin update-project](#apolo-admin-update-project)_| Update project settings |
| _[apolo admin update\-project-user](#apolo-admin-update-project-user)_| Update user access to specified project |
| _[apolo admin update\-resource-preset](#apolo-admin-update-resource-preset)_| Update existing resource preset |




### apolo admin add-cluster

Create a new cluster.<br/><br/>Creates cluster entry on admin side and then start its provisioning using<br/>provided config.

**Usage:**

```bash
apolo admin add-cluster [OPTIONS] CLUSTER_NAME CONFIG
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--default-credits AMOUNT_|Default credits amount to set \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-jobs AMOUNT_|Default maximum running jobs quota \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-role \[ROLE]_|Default role for new users added to cluster  \[default: user]|




### apolo admin add-cluster-user

Add user access to a specified cluster.<br/><br/>The command supports one of three user roles: admin, manager or user.

**Usage:**

```bash
apolo admin add-cluster-user [OPTIONS] CLUSTER_NAME USER_NAME [ROLE]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-j, --jobs AMOUNT_|Maximum running jobs quota \(`unlimited' stands for no limit)|
|_--org ORG_|org name for org-cluster users|




### apolo admin add-org

Create a new org.

**Usage:**

```bash
apolo admin add-org [OPTIONS] ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo admin add-org-cluster

Add org access to specified cluster.

**Usage:**

```bash
apolo admin add-org-cluster [OPTIONS] CLUSTER_NAME ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-c, --credits AMOUNT_|Credits amount to set \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-credits AMOUNT_|Default credits amount to set \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-jobs AMOUNT_|Default maximum running jobs quota \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-role \[ROLE]_|Default role for new users added to org cluster  \[default: user]|
|_\-j, --jobs AMOUNT_|Maximum running jobs quota \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--storage-size AMOUNT_|Storage size, ignored for storage types with elastic storage size|




### apolo admin add-org-credits

Add given values to org balance

**Usage:**

```bash
apolo admin add-org-credits [OPTIONS] ORG
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-c, --credits AMOUNT_|Credits amount to add|




### apolo admin add-org-user

Add user access to specified org.<br/><br/>The command supports one of three user roles: admin, manager or user.

**Usage:**

```bash
apolo admin add-org-user [OPTIONS] ORG_NAME USER_NAME [ROLE]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-c, --credits AMOUNT_|Credits amount to set \(`unlimited' stands for no limit)|




### apolo admin add-project

Add new project to specified cluster.

**Usage:**

```bash
apolo admin add-project [OPTIONS] CLUSTER_NAME NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--default_|Is this project is default, e.g. new cluster users will be automatically added to it|
|_\--default-role \[ROLE]_|Default role for new users added to project  \[default: writer]|
|_--org ORG_|org name for org-cluster projects|




### apolo admin add-project-user

Add user access to specified project.<br/><br/>The command supports one of 4 user roles: reader, writer, manager or admin.

**Usage:**

```bash
apolo admin add-project-user [OPTIONS] CLUSTER_NAME PROJECT_NAME
                                    USER_NAME [ROLE]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--org ORG_|org name for org-cluster projects|




### apolo admin add-resource-preset

Add new resource preset

**Usage:**

```bash
apolo admin add-resource-preset [OPTIONS] PRESET_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--amd-gpu NUMBER_|Number of AMD GPUs|
|_\--amd-gpu-model GPU\_MODEL_FREE_TEXT_|AMD GPU model|
|_\-c, --cpu NUMBER_|Number of CPUs  \[default: 0.1]|
|_\--credits-per-hour AMOUNT_|Price of running job of this preset for an hour in credits  \[default: 0]|
|_\--intel-gpu NUMBER_|Number of Intel GPUs|
|_\--intel-gpu-model GPU\_MODEL_FREE_TEXT_|Intel GPU model|
|_\-m, --memory AMOUNT_|Memory amount  \[default: 1GB]|
|_\-g, --nvidia-gpu NUMBER_|Number of Nvidia GPUs|
|_\--nvidia-gpu-model GPU\_MODEL_FREE_TEXT_|Nvidia GPU model|
|_\--preemptible-node / --non-preemptible-node_|Use a lower\-cost preemptible instance  \[default: non-preemptible-node]|
|_\-r, --resource-pool TEXT_|Name of the resource pool where job will be scheduled \(multiple values are supported)|
|_\-p, --scheduler / -P, --no-scheduler_|Use round robin scheduler for jobs  \[default: no-scheduler]|
|_\--tpu-sw-version VERSION_|TPU software version|
|_\--tpu-type TYPE_|TPU type|




### apolo admin add-user-credits

Add given values to user credits

**Usage:**

```bash
apolo admin add-user-credits [OPTIONS] ORG USER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-c, --credits AMOUNT_|Credits amount to add  \[required]|




### apolo admin generate-cluster-config

Create a cluster configuration file.

**Usage:**

```bash
apolo admin generate-cluster-config [OPTIONS] [CONFIG]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--type \[aws &#124; gcp &#124; azure &#124; vcd]_||




### apolo admin get-cluster-orgs

Print the list of all orgs in the cluster

**Usage:**

```bash
apolo admin get-cluster-orgs [OPTIONS] CLUSTER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo admin get-cluster-users

List users in specified cluster

**Usage:**

```bash
apolo admin get-cluster-users [OPTIONS] [CLUSTER_NAME]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--details / --no-details_|Include detailed user info|
|_--org ORG_|org name for org-cluster users|




### apolo admin get-clusters

Print the list of available clusters.

**Usage:**

```bash
apolo admin get-clusters [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo admin get-org-cluster-quota

Get info about org quota in given cluster

**Usage:**

```bash
apolo admin get-org-cluster-quota [OPTIONS] CLUSTER_NAME ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo admin get-org-users

List users in specified org

**Usage:**

```bash
apolo admin get-org-users [OPTIONS] ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo admin get-orgs

Print the list of available orgs.

**Usage:**

```bash
apolo admin get-orgs [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo admin get-project-users

List users in specified project

**Usage:**

```bash
apolo admin get-project-users [OPTIONS] CLUSTER_NAME PROJECT_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--org ORG_|org name for org-cluster projects|




### apolo admin get-projects

Print the list of all projects in the cluster

**Usage:**

```bash
apolo admin get-projects [OPTIONS] CLUSTER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--org ORG_|org name for org-cluster projects|




### apolo admin get-user-quota

Get info about user quota in given cluster

**Usage:**

```bash
apolo admin get-user-quota [OPTIONS] CLUSTER_NAME USER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--org ORG_|org name for org-cluster users|




### apolo admin remove-cluster

Drop a cluster<br/><br/>Completely removes cluster from the system.

**Usage:**

```bash
apolo admin remove-cluster [OPTIONS] CLUSTER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--force_|Skip prompt|




### apolo admin remove-cluster-user

Remove user access from the cluster.

**Usage:**

```bash
apolo admin remove-cluster-user [OPTIONS] CLUSTER_NAME USER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--org ORG_|org name for org-cluster users|




### apolo admin remove-org

Drop an org<br/><br/>Completely removes org from the system.

**Usage:**

```bash
apolo admin remove-org [OPTIONS] ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--force_|Skip prompt|




### apolo admin remove-org-cluster

Drop an org cluster<br/><br/>Completely removes org from the cluster.

**Usage:**

```bash
apolo admin remove-org-cluster [OPTIONS] CLUSTER_NAME ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--force_|Skip prompt|




### apolo admin remove-org-user

Remove user access from the org.

**Usage:**

```bash
apolo admin remove-org-user [OPTIONS] ORG_NAME USER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo admin remove-project

Drop a project<br/><br/>Completely removes project from the cluster.

**Usage:**

```bash
apolo admin remove-project [OPTIONS] CLUSTER_NAME NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--force_|Skip prompt|
|_--org ORG_|org name for org-cluster projects|




### apolo admin remove-project-user

Remove user access from the project.

**Usage:**

```bash
apolo admin remove-project-user [OPTIONS] CLUSTER_NAME PROJECT_NAME
                                       USER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--org ORG_|org name for org-cluster projects|




### apolo admin remove-resource-preset

Remove resource preset

**Usage:**

```bash
apolo admin remove-resource-preset [OPTIONS] PRESET_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo admin set-org-cluster-defaults

Set org cluster defaults to given value

**Usage:**

```bash
apolo admin set-org-cluster-defaults [OPTIONS] CLUSTER_NAME ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--default-credits AMOUNT_|Default credits amount to set \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-jobs AMOUNT_|Default maximum running jobs quota \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-role \[ROLE]_|Default role for new users added to org cluster  \[default: user]|




### apolo admin set-org-cluster-quota

Set org cluster quota to given values

**Usage:**

```bash
apolo admin set-org-cluster-quota [OPTIONS] CLUSTER_NAME ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-j, --jobs AMOUNT_|Maximum running jobs quota \(`unlimited' stands for no limit)  \[required]|




### apolo admin set-org-credits

Set org credits to given value

**Usage:**

```bash
apolo admin set-org-credits [OPTIONS] ORG
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-c, --credits AMOUNT_|Credits amount to set \(`unlimited' stands for no limit)  \[required]|




### apolo admin set-org-defaults

Set org defaults to a given value

**Usage:**

```bash
apolo admin set-org-defaults [OPTIONS] ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--user-default-credits AMOUNT_|Default credits amount to set for org users \(`unlimited' stands for no limit)  \[default: unlimited]|




### apolo admin set-user-credits

Set user credits to given value

**Usage:**

```bash
apolo admin set-user-credits [OPTIONS] ORG USER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-c, --credits AMOUNT_|Credits amount to set \(`unlimited' stands for no limit)  \[required]|




### apolo admin set-user-quota

Set user quota to given values

**Usage:**

```bash
apolo admin set-user-quota [OPTIONS] CLUSTER_NAME USER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-j, --jobs AMOUNT_|Maximum running jobs quota \(`unlimited' stands for no limit)  \[required]|
|_--org ORG_|org name for org-cluster users|




### apolo admin show-cluster-options

Show available cluster options.

**Usage:**

```bash
apolo admin show-cluster-options [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--type \[aws &#124; gcp &#124; azure]_||




### apolo admin update-cluster

Update a cluster.

**Usage:**

```bash
apolo admin update-cluster [OPTIONS] CLUSTER_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--default-credits AMOUNT_|Default credits amount to set \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-jobs AMOUNT_|Default maximum running jobs quota \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-role \[ROLE]_|Default role for new users added to cluster  \[default: user]|




### apolo admin update-cluster-user

**Usage:**

```bash
apolo admin update-cluster-user [OPTIONS] CLUSTER_NAME USER_NAME [ROLE]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--org ORG_|org name for org-cluster users|




### apolo admin update-node-pool

Update cluster node pool.

**Usage:**

```bash
apolo admin update-node-pool [OPTIONS] CLUSTER_NAME NODE_POOL_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--idle-size NUMBER_|Number of idle nodes in the node pool.|




### apolo admin update-org-cluster

Update org cluster quotas.

**Usage:**

```bash
apolo admin update-org-cluster [OPTIONS] CLUSTER_NAME ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-c, --credits AMOUNT_|Credits amount to set \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-credits AMOUNT_|Default credits amount to set \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-jobs AMOUNT_|Default maximum running jobs quota \(`unlimited' stands for no limit)  \[default: unlimited]|
|_\--default-role \[ROLE]_|Default role for new users added to org cluster  \[default: user]|
|_\-j, --jobs AMOUNT_|Maximum running jobs quota \(`unlimited' stands for no limit)  \[default: unlimited]|




### apolo admin update-project

Update project settings.

**Usage:**

```bash
apolo admin update-project [OPTIONS] CLUSTER_NAME NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--default_|Is this project is default, e.g. new cluster users will be automatically added to it|
|_\--default-role \[ROLE]_|Default role for new users added to project  \[default: writer]|
|_--org ORG_|org name for org-cluster projects|




### apolo admin update-project-user

Update user access to specified project.<br/><br/>The command supports one of 4 user roles: reader, writer, manager or admin.

**Usage:**

```bash
apolo admin update-project-user [OPTIONS] CLUSTER_NAME PROJECT_NAME
                                       USER_NAME [ROLE]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--org ORG_|org name for org-cluster projects|




### apolo admin update-resource-preset

Update existing resource preset

**Usage:**

```bash
apolo admin update-resource-preset [OPTIONS] PRESET_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--amd-gpu NUMBER_|Number of AMD GPUs|
|_\--amd-gpu-model GPU\_MODEL_FREE_TEXT_|AMD GPU model|
|_\-c, --cpu NUMBER_|Number of CPUs|
|_\--credits-per-hour AMOUNT_|Price of running job of this preset for an hour in credits|
|_\--intel-gpu NUMBER_|Number of Intel GPUs|
|_\--intel-gpu-model GPU\_MODEL_FREE_TEXT_|Intel GPU model|
|_\-m, --memory AMOUNT_|Memory amount|
|_\-g, --nvidia-gpu NUMBER_|Number of Nvidia GPUs|
|_\--nvidia-gpu-model GPU\_MODEL_FREE_TEXT_|Nvidia GPU model|
|_\--preemptible-node / --non-preemptible-node_|Use a lower-cost preemptible instance|
|_\-r, --resource-pool TEXT_|Name of the resource pool where job will be scheduled \(multiple values are supported)|
|_\-p, --scheduler / -P, --no-scheduler_|Use round robin scheduler for jobs|
|_\--tpu-sw-version VERSION_|TPU software version|
|_\--tpu-type TYPE_|TPU type|




## apolo app

Operations with applications.

**Usage:**

```bash
apolo app [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo app list](#apolo-app-list)_| List all apps |




### apolo app list

List all apps.

**Usage:**

```bash
apolo app list [OPTIONS] [CLUSTER] [ORG] [PROJECT]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo blob

Blob storage operations.

**Usage:**

```bash
apolo blob [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo blob cp](#apolo-blob-cp)_| Copy blobs into and from Blob Storage |
| _[apolo blob du](#apolo-blob-du)_| Get storage usage for BUCKET |
| _[apolo blob glob](#apolo-blob-glob)_| List resources that match PATTERNS |
| _[apolo blob importbucket](#apolo-blob-importbucket)_| Import an existing bucket |
| _[apolo blob ls](#apolo-blob-ls)_| List buckets or bucket contents |
| _[apolo blob lsbucket](#apolo-blob-lsbucket)_| List buckets |
| _[apolo blob lscredentials](#apolo-blob-lscredentials)_| List bucket credentials |
| _[apolo blob mkbucket](#apolo-blob-mkbucket)_| Create a new bucket |
| _[apolo blob mkcredentials](#apolo-blob-mkcredentials)_| Create a new bucket credential |
| _[apolo blob rm](#apolo-blob-rm)_| Remove blobs from bucket |
| _[apolo blob rmbucket](#apolo-blob-rmbucket)_| Remove bucket BUCKET |
| _[apolo blob rmcredentials](#apolo-blob-rmcredentials)_| Remove bucket credential BUCKET_CREDENTIAL |
| _[apolo blob set\-bucket-publicity](#apolo-blob-set-bucket-publicity)_| Change public access settings for BUCKET |
| _[apolo blob sign-url](#apolo-blob-sign-url)_| Make signed url for blob in bucket |
| _[apolo blob statbucket](#apolo-blob-statbucket)_| Get bucket BUCKET |
| _[apolo blob statcredentials](#apolo-blob-statcredentials)_| Get bucket credential BUCKET_CREDENTIAL |




### apolo blob cp

Copy blobs into and from Blob Storage.<br/><br/>Either SOURCES or DESTINATION should have `blob://` scheme. If scheme is<br/>omitted, file:// scheme is assumed. It is currently not possible to copy files<br/>between Blob Storage \(`blob://`) destination, nor with `storage://` scheme<br/>paths.<br/><br/>Use `/dev/stdin` and `/dev/stdout` file names to upload a file from standard<br/>input or output to stdout.<br/><br/>Any number of \--exclude and --include options can be passed.  The filters that<br/>appear later in the command take precedence over filters that appear earlier<br/>in the command.  If neither \--exclude nor --include options are specified the<br/>default can be changed using the storage.cp-exclude configuration variable<br/>documented in "apolo help user-config".<br/><br/>File permissions, modification times and other attributes will not be passed<br/>to Blob Storage metadata during upload.

**Usage:**

```bash
apolo blob cp [OPTIONS] [SOURCES]... [DESTINATION]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--continue_|Continue copying partially-copied files. Only for copying from Blob Storage.|
|_\--exclude-from-files FILES_|A list of file names that contain patterns for exclusion files and directories. Used only for uploading. The default can be changed using the storage.cp\-exclude-from-files configuration variable documented in "apolo help user-config"|
|_--exclude TEXT_|Exclude files and directories that match the specified pattern.|
|_--include TEXT_|Don't exclude files and directories that match the specified pattern.|
|_\--glob / --no-glob_|Expand glob patterns in SOURCES with explicit scheme.  \[default: glob]|
|_\-T, --no-target-directory_|Treat DESTINATION as a normal file.|
|_\-p, --progress / -P, --no-progress_|Show progress, on by default.|
|_\-r, --recursive_|Recursive copy, off by default|
|_\-t, --target-directory DIRECTORY_|Copy all SOURCES into DIRECTORY.|
|_\-u, --update_|Copy only when the SOURCE file is newer than the destination file or when the destination file is missing.|




### apolo blob du

Get storage usage for BUCKET.

**Usage:**

```bash
apolo blob du [OPTIONS] BUCKET
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Look on a specified cluster \(the current cluster by default).|
|_--org ORG_|Look on a specified org \(the current org by default).|
|_--project PROJECT_|Look on a specified project \(the current project by default).|




### apolo blob glob

List resources that match PATTERNS.

**Usage:**

```bash
apolo blob glob [OPTIONS] [PATTERNS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--full-uri_|Output full bucket URI.|




### apolo blob importbucket

Import an existing bucket.

**Usage:**

```bash
apolo blob importbucket [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--aws-access-key-id AWS\_ACCESS_KEY_ID_|AWS access\_key_id to use to access the bucket.  Required when PROVIDER is 'aws'|
|_\--aws-endpoint-url AWS_ENDPOINT_|AWS endpoint to use to access the bucket. Usually you need to set this if you use non-AWS S3 compatible provider|
|_\--aws-region-name AWS_REGION_|AWS region to use to access the bucket.|
|_\--aws-secret-access-key AWS\_SECRET_ACCESS_KEY_|AWS secret\_access_key to use to access the bucket. Required when PROVIDER is 'aws'|
|_\--azure-storage-account-url AZURE\_STORAGE_ACCOUNT_URL_|Azure account url. Usually it has following format: https://<account_id>.blob.core.windows.net Required when PROVIDER is 'azure'|
|_\--azure-storage-credential AZURE\_STORAGE_CREDENTIAL_|Azure storage credential that grants access to imported bucket. Either this or AZURE_SAS is required when PROVIDER is 'azure'|
|_\--azure-storage-sas-token AZURE_SAS_|Azure shared access signature token that grants access to imported bucket. Either this or AZURE\_STORAGE_CREDENTIAL is required when PROVIDER is 'azure'|
|_--cluster CLUSTER_|Perform in a specified cluster \(the current cluster by default).|
|_\--gcp-sa-credential GCP\_SA_CREDNETIAL_|GCP service account credential in form of base64 encoded json string that grants access to imported bucket. Required when PROVIDER is 'gcp'|
|_--name NAME_|Optional bucket name|
|_--org ORG_|Perform in a specified org \(the current org by default).|
|_--project PROJECT_|Perform in a specified project \(the current project by default).|
|_--provider PROVIDER_|Bucket provider that hosts bucket  \[required]|
|_\--provider-bucket-name EXTERNAL_NAME_|Name of bucket \(or container in case of Azure) inside the provider  \[required]|




### apolo blob ls

List buckets or bucket contents.

**Usage:**

```bash
apolo blob ls [OPTIONS] [PATHS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_-l_|use a long listing format.|
|_\--full-uri_|Output full bucket URI.|
|_\-h, --human-readable_|with -l print human readable sizes \(e.g., 2K, 540M).|
|_\-r, --recursive_|List all keys under the URL path provided, not just 1 level depths.|




### apolo blob lsbucket

List buckets.

**Usage:**

```bash
apolo blob lsbucket [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--all-orgs_|Show buckets in all orgs.|
|_\--all-projects_|Show buckets in all projects.|
|_--cluster CLUSTER_|Look on a specified cluster \(the current cluster by default).|
|_\--full-uri_|Output full bucket URI.|
|_\--long-format_|Output all info about bucket.|
|_--org ORG_|Look on a specified org \(the current org by default).|
|_--project PROJECT_|Look on a specified project \(the current project by default).|




### apolo blob lscredentials

List bucket credentials.

**Usage:**

```bash
apolo blob lscredentials [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Look on a specified cluster \(the current cluster by default).|




### apolo blob mkbucket

Create a new bucket.

**Usage:**

```bash
apolo blob mkbucket [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Perform in a specified cluster \(the current cluster by default).|
|_--name NAME_|Optional bucket name|
|_--org ORG_|Perform in a specified org \(the current org by default).|
|_--project PROJECT_|Perform in a specified project \(the current project by default).|




### apolo blob mkcredentials

Create a new bucket credential.

**Usage:**

```bash
apolo blob mkcredentials [OPTIONS] BUCKETS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Perform in a specified cluster \(the current cluster by default).|
|_--name NAME_|Optional bucket credential name|
|_--org ORG_|Perform in a specified org \(the current org by default).|
|_--project PROJECT_|Perform in a specified project \(the current project by default).|
|_\--read-only_|Make read-only credential|




### apolo blob rm

Remove blobs from bucket.

**Usage:**

```bash
apolo blob rm [OPTIONS] PATHS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--glob / --no-glob_|Expand glob patterns in PATHS  \[default: glob]|
|_\-p, --progress / -P, --no-progress_|Show progress, on by default in TTY mode, off otherwise.|
|_\-r, --recursive_|remove directories and their contents recursively|




### apolo blob rmbucket

Remove bucket BUCKET.

**Usage:**

```bash
apolo blob rmbucket [OPTIONS] BUCKETS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Perform on a specified cluster \(the current cluster by default).|
|_\-f, --force_|Force removal of all blobs inside bucket|
|_--org ORG_|Perform on a specified org \(the current org by default).|
|_--project PROJECT_|Perform on a specified project \(the current project by default).|




### apolo blob rmcredentials

Remove bucket credential BUCKET_CREDENTIAL.

**Usage:**

```bash
apolo blob rmcredentials [OPTIONS] CREDENTIALS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Perform on a specified cluster \(the current cluster by default).|




### apolo blob set-bucket-publicity

Change public access settings for BUCKET<br/>

**Usage:**

```bash
apolo blob set-bucket-publicity [OPTIONS] BUCKET {public|private}
```

**Examples:**

```bash

apolo blob set-bucket-publicity my-bucket public
apolo blob set-bucket-publicity my-bucket private

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Perform on a specified cluster \(the current cluster by default).|
|_--org ORG_|Perform on a specified org \(the current org by default).|
|_--project PROJECT_|Perform on a specified project \(the current project by default).|




### apolo blob sign-url

Make signed url for blob in bucket.

**Usage:**

```bash
apolo blob sign-url [OPTIONS] PATH
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--expires TIMEDELTA_|Duration this signature will be valid in the format '1h2m3s'  \[default: 1h]|




### apolo blob statbucket

Get bucket BUCKET.

**Usage:**

```bash
apolo blob statbucket [OPTIONS] BUCKET
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Look on a specified cluster \(the current cluster by default).|
|_\--full-uri_|Output full bucket URI.|
|_--org ORG_|Look on a specified org \(the current org by default).|
|_--project PROJECT_|Look on a specified project \(the current project by default).|




### apolo blob statcredentials

Get bucket credential BUCKET_CREDENTIAL.

**Usage:**

```bash
apolo blob statcredentials [OPTIONS] BUCKET_CREDENTIAL
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Look on a specified cluster \(the current cluster by default).|




## apolo completion

Output shell completion code.

**Usage:**

```bash
apolo completion [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo completion generate](#apolo-completion-generate)_| Show instructions for shell completion |
| _[apolo completion patch](#apolo-completion-patch)_| Patch shell profile to enable completion |




### apolo completion generate

Show instructions for shell completion.

**Usage:**

```bash
apolo completion generate [OPTIONS] {bash|zsh}
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo completion patch

Patch shell profile to enable completion<br/><br/>Patches shell configuration while depending of current shell. Files patched:<br/><br/>bash: `~/.bashrc` zsh: `~/.zshrc`

**Usage:**

```bash
apolo completion patch [OPTIONS] {bash|zsh}
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo config

Client configuration.

**Usage:**

```bash
apolo config [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo config aliases](#apolo-config-aliases)_| List available command aliases |
| _[apolo config docker](#apolo-config-docker)_| Configure local docker client |
| _[apolo config get-clusters](#apolo-config-get-clusters)_| List available clusters/org pairs |
| _[apolo config login](#apolo-config-login)_| Log into Apolo Platform |
| _[apolo config login-headless](#apolo-config-login-headless)_| Log into Apolo Platform in non-GUI environ |
| _[apolo config login\-with-token](#apolo-config-login-with-token)_| Log into Apolo Platform with token |
| _[apolo config logout](#apolo-config-logout)_| Log out |
| _[apolo config show](#apolo-config-show)_| Print current settings |
| _[apolo config show-token](#apolo-config-show-token)_| Print current authorization token |
| _[apolo config switch-cluster](#apolo-config-switch-cluster)_| Switch the active cluster |
| _[apolo config switch-org](#apolo-config-switch-org)_| Switch the active organization |
| _[apolo config switch-project](#apolo-config-switch-project)_| Switch the active project |




### apolo config aliases

List available command aliases.

**Usage:**

```bash
apolo config aliases [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo config docker

Configure local docker client<br/><br/>This command configures local docker client to use Apolo Platform's docker<br/>registry.

**Usage:**

```bash
apolo config docker [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--docker-config PATH_|Specifies the location of the Docker client configuration files|




### apolo config get-clusters

List available clusters/org pairs.<br/><br/>This command re-fetches cluster list and then displays each cluster with<br/>available orgs.

**Usage:**

```bash
apolo config get-clusters [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo config login

Log into Apolo Platform.<br/><br/>URL is a platform entrypoint URL.

**Usage:**

```bash
apolo config login [OPTIONS] [URL]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo config login-headless

Log into Apolo Platform in non-GUI environ<br/><br/>URL is a platform entrypoint URL.<br/><br/>The command works similar to "apolo login" but instead of opening a browser<br/>for performing OAuth registration prints an URL that should be open on guest<br/>host.<br/><br/>Then user inputs a code displayed in a browser after successful login back in<br/>apolo command to finish the login process.

**Usage:**

```bash
apolo config login-headless [OPTIONS] [URL]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo config login-with-token

Log into Apolo Platform with token.<br/><br/>TOKEN is authentication token provided by administration team. URL is a<br/>platform entrypoint URL.

**Usage:**

```bash
apolo config login-with-token [OPTIONS] TOKEN [URL]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo config logout

Log out.

**Usage:**

```bash
apolo config logout [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo config show

Print current settings.

**Usage:**

```bash
apolo config show [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--energy_|Including cluster energy consumption and CO2 emissions information|




### apolo config show-token

Print current authorization token.

**Usage:**

```bash
apolo config show-token [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo config switch-cluster

Switch the active cluster.<br/><br/>CLUSTER_NAME is the cluster name to select.  The interactive prompt is used if<br/>the name is omitted \(default).

**Usage:**

```bash
apolo config switch-cluster [OPTIONS] [CLUSTER_NAME]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo config switch-org

Switch the active organization.<br/><br/>ORG_NAME is the organization name to select.

**Usage:**

```bash
apolo config switch-org [OPTIONS] ORG_NAME
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo config switch-project

Switch the active project.<br/><br/>PROJECT_NAME is the project name to select. The interactive prompt is used if<br/>the name is omitted \(default).

**Usage:**

```bash
apolo config switch-project [OPTIONS] [PROJECT_NAME]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo disk

Operations with disks.

**Usage:**

```bash
apolo disk [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo disk create](#apolo-disk-create)_| Create a disk |
| _[apolo disk get](#apolo-disk-get)_| Get disk DISK_ID |
| _[apolo disk ls](#apolo-disk-ls)_| List disks |
| _[apolo disk rm](#apolo-disk-rm)_| Remove disk DISK_ID |




### apolo disk create

Create a disk<br/><br/>Create a disk with at least storage amount STORAGE.<br/><br/>To specify the amount, you can use the following suffixes: "kKMGTPEZY" To use<br/>decimal quantities, append "b" or "B". For example: - 1K or 1k is 1024 bytes -<br/>1Kb or 1KB is 1000 bytes - 20G is 20 * 2 ^ 30 bytes - 20Gb or 20GB is<br/>20.000.000.000 bytes<br/><br/>Note that server can have big granularity \(for example, 1G) so it will<br/>possibly round-up the amount you requested.<br/>

**Usage:**

```bash
apolo disk create [OPTIONS] STORAGE
```

**Examples:**

```bash

apolo disk create 10G
apolo disk create 500M

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Perform in a specified cluster \(the current cluster by default).|
|_--name NAME_|Optional disk name|
|_--org ORG_|Perform in a specified org \(the current org by default).|
|_--project PROJECT_|Create disk in a specified project \(the current project by default).|
|_\--timeout-unused TIMEDELTA_|Optional disk lifetime limit after last usage in the format '1d2h3m4s' \(some parts may be missing). Set '0' to disable. Default value '1d' can be changed in the user config.|




### apolo disk get

Get disk DISK_ID.

**Usage:**

```bash
apolo disk get [OPTIONS] DISK
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Look on a specified cluster \(the current cluster by default).|
|_\--full-uri_|Output full disk URI.|
|_--org ORG_|Look on a specified org \(the current org by default).|
|_--project PROJECT_|Look on a specified project \(the current project by default).|




### apolo disk ls

List disks.

**Usage:**

```bash
apolo disk ls [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--all-orgs_|Show disks in all orgs.|
|_\--all-projects_|Show disks in all projects.|
|_--cluster CLUSTER_|Look on a specified cluster \(the current cluster by default).|
|_\--full-uri_|Output full disk URI.|
|_\--long-format_|Output all info about disk.|
|_--org ORG_|Look on a specified org \(the current org by default).|
|_--project PROJECT_|Look on a specified project \(the current project by default).|




### apolo disk rm

Remove disk DISK_ID.

**Usage:**

```bash
apolo disk rm [OPTIONS] DISKS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Perform on a specified cluster \(the current cluster by default).|
|_--org ORG_|Perform on a specified org \(the current org by default).|
|_--project PROJECT_|Perform on a specified project \(the current project by default).|




## apolo image

Container image operations.

**Usage:**

```bash
apolo image [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo image digest](#apolo-image-digest)_| Get digest of an image from remote registry |
| _[apolo image ls](#apolo-image-ls)_| List images |
| _[apolo image pull](#apolo-image-pull)_| Pull an image from platform registry |
| _[apolo image push](#apolo-image-push)_| Push an image to platform registry |
| _[apolo image rm](#apolo-image-rm)_| Remove image from platform registry |
| _[apolo image size](#apolo-image-size)_| Get image size |
| _[apolo image tags](#apolo-image-tags)_| List tags for image in platform registry |




### apolo image digest

Get digest of an image from remote registry<br/><br/>Image name must be URL with image:// scheme. Image name must contain tag.<br/>

**Usage:**

```bash
apolo image digest [OPTIONS] IMAGE
```

**Examples:**

```bash

apolo image digest image:/other-project/alpine:shared
apolo image digest image:myimage:latest

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo image ls

List images.

**Usage:**

```bash
apolo image ls [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--all-orgs_|Show images in all orgs.|
|_\--all-projects_|Show images in all projects.|
|_--cluster CLUSTER_|Show images on a specified cluster \(the current cluster by default).|
|_-l_|List in long format.|
|_\--full-uri_|Output full image URI.|
|_\-n, --name PATTERN_|Filter out images by name regex.|
|_--org ORG_|Filter out images by org \(multiple option, the current org by default).|
|_--project PROJECT_|Filter out images by project \(multiple option, the current project by default).|




### apolo image pull

Pull an image from platform registry.<br/><br/>Remote image name must be URL with image:// scheme. Image names can contain<br/>tag.<br/>

**Usage:**

```bash
apolo image pull [OPTIONS] REMOTE_IMAGE [LOCAL_IMAGE]
```

**Examples:**

```bash

apolo pull image:myimage
apolo pull image:/other-project/alpine:shared
apolo pull image:/project/my-alpine:production alpine:from-registry

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo image push

Push an image to platform registry.<br/><br/>Remote image must be URL with image:// scheme. Image names can contain tag. If<br/>tags not specified 'latest' will be used as value.<br/>

**Usage:**

```bash
apolo image push [OPTIONS] LOCAL_IMAGE [REMOTE_IMAGE]
```

**Examples:**

```bash

apolo push myimage
apolo push alpine:latest image:my-alpine:production
apolo push alpine image:/other-project/alpine:shared

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo image rm

Remove image from platform registry.<br/><br/>Image name must be URL with image:// scheme. Image name must contain tag.<br/>

**Usage:**

```bash
apolo image rm [OPTIONS] IMAGES...
```

**Examples:**

```bash

apolo image rm image:/other-project/alpine:shared
apolo image rm image:myimage:latest

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_-f_|Force deletion of all tags referencing the image.|




### apolo image size

Get image size<br/><br/>Image name must be URL with image:// scheme. Image name must contain tag.<br/>

**Usage:**

```bash
apolo image size [OPTIONS] IMAGE
```

**Examples:**

```bash

apolo image size image:/other-project/alpine:shared
apolo image size image:myimage:latest

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo image tags

List tags for image in platform registry.<br/><br/>Image name must be URL with image:// scheme.<br/>

**Usage:**

```bash
apolo image tags [OPTIONS] IMAGE
```

**Examples:**

```bash

apolo image tags image:/other-project/alpine
apolo image tags -l image:myimage

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_-l_|List in long format, with image sizes.|




## apolo job

Job operations.

**Usage:**

```bash
apolo job [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo job attach](#apolo-job-attach)_| Attach terminal to a job |
| _[apolo job browse](#apolo-job-browse)_| Opens a job's URL in a web browser |
| _[apolo job bump\-life-span](#apolo-job-bump-life-span)_| Increase job life span |
| _[apolo job exec](#apolo-job-exec)_| Execute command in a running job |
| _[apolo job generate\-run-command](#apolo-job-generate-run-command)_| Generate command that will rerun given job |
| _[apolo job kill](#apolo-job-kill)_| Kill job\(s) |
| _[apolo job logs](#apolo-job-logs)_| Print the logs for a job |
| _[apolo job ls](#apolo-job-ls)_| List all jobs |
| _[apolo job port-forward](#apolo-job-port-forward)_| Forward port\(s) of a job |
| _[apolo job run](#apolo-job-run)_| Run a job |
| _[apolo job save](#apolo-job-save)_| Save job's state to an image |
| _[apolo job status](#apolo-job-status)_| Display status of a job |
| _[apolo job top](#apolo-job-top)_| Display GPU/CPU/Memory usage |




### apolo job attach

Attach terminal to a job<br/><br/>Attach local standard input, output, and error streams to a running job.

**Usage:**

```bash
apolo job attach [OPTIONS] JOB
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--port-forward LOCAL\_PORT:REMOTE_RORT_|Forward port\(s) of a running job to local port\(s) \(use multiple times for forwarding several ports)|




### apolo job browse

Opens a job's URL in a web browser.

**Usage:**

```bash
apolo job browse [OPTIONS] JOB
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo job bump-life-span

Increase job life span

**Usage:**

```bash
apolo job bump-life-span [OPTIONS] JOB TIMEDELTA
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo job exec

Execute command in a running job.<br/>

**Usage:**

```bash
apolo job exec [OPTIONS] JOB -- CMD...
```

**Examples:**

```bash

# Provides a shell to the container:
apolo exec my-job -- /bin/bash

# Executes a single command in the container and returns the control:
apolo exec --no-tty my-job -- ls -l

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-t, --tty / -T, --no-tty_|Allocate a TTY, can be useful for interactive jobs. By default is on if the command is executed from a terminal, non-tty mode is used if executed from a script.|




### apolo job generate-run-command

Generate command that will rerun given job.<br/>

**Usage:**

```bash
apolo job generate-run-command [OPTIONS] JOB
```

**Examples:**

```bash

# You can use the following to directly re-execute it:
eval $(apolo job generate-run-command <job-id>)

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo job kill

Kill job\(s).

**Usage:**

```bash
apolo job kill [OPTIONS] JOBS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo job logs

Print the logs for a job.

**Usage:**

```bash
apolo job logs [OPTIONS] JOB
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--since DATE\_OR_TIMEDELTA_|Only return logs after a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|
|_--timestamps_|Include timestamps on each line in the log output.|




### apolo job ls

List all jobs.<br/>

**Usage:**

```bash
apolo job ls [OPTIONS]
```

**Examples:**

```bash

apolo ps -a
apolo ps -a --owner=user-1 --owner=user-2
apolo ps --name my-experiments-v1 -s failed -s succeeded
apolo ps --description=my favourite job
apolo ps -s failed -s succeeded -q
apolo ps -t tag1 -t tag2

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-a, --all_|Show all jobs regardless the status.|
|_\--all-orgs_|Show jobs in all orgs.|
|_\--all-projects_|Show jobs in all projects.|
|_--cluster CLUSTER_|Show jobs on a specified cluster \(the current cluster by default).|
|_\-d, --description DESCRIPTION_|Filter out jobs by description \(exact match).|
|_--distinct_|Show only first job if names are same.|
|_--format COLUMNS_|Output table format, see "apolo help ps\-format" for more info about the format specification. The default can be changed using the job.ps-format configuration variable documented in "apolo help user-config"|
|_\--full-uri_|Output full image URI.|
|_\-n, --name NAME_|Filter out jobs by name.|
|_--org ORG_|Filter out jobs by org name \(multiple option, the current org by default).|
|_\-o, --owner TEXT_|Filter out jobs by owner \(multiple option). Supports `ME` option to filter by the current user.|
|_\-p, --project PROJECT_|Filter out jobs by project name \(multiple option, the current project by default).|
|_\--recent-first / --recent-last_|Show newer jobs first or last|
|_--since DATE\_OR_TIMEDELTA_|Show jobs created after a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|
|_\-s, --status \[pending &#124; suspended &#124; running &#124; succeeded &#124; failed &#124; cancelled]_|Filter out jobs by status \(multiple option).|
|_\-t, --tag TAG_|Filter out jobs by tag \(multiple option)|
|_--until DATE\_OR_TIMEDELTA_|Show jobs created before a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|
|_\-w, --wide_|Do not cut long lines for terminal width.|




### apolo job port-forward

Forward port\(s) of a job.<br/><br/>Forwards port\(s) of a running job to local port\(s).<br/>

**Usage:**

```bash
apolo job port-forward [OPTIONS] JOB LOCAL_PORT:REMOTE_RORT...
```

**Examples:**

```bash

# Forward local port 2080 to port 80 of job's container.
# You can use http://localhost:2080 in browser to access job's served http
apolo job port-forward my-fastai-job 2080:80

# Forward local port 2222 to job's port 22
# Then copy all data from container's folder '/data' to current folder
# (please run second command in other terminal)
apolo job port-forward my-job-with-ssh-server 2222:22
rsync -avxzhe ssh -p 2222 root@localhost:/data .

# Forward few ports at once
apolo job port-forward my-job 2080:80 2222:22 2000:100

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo job run

Run a job<br/><br/>IMAGE docker image name to run in a job.<br/><br/>CMD list will be passed as arguments to the executed job's image.<br/>

**Usage:**

```bash
apolo job run [OPTIONS] IMAGE [-- CMD...]
```

**Examples:**

```bash

# Starts a container pytorch/pytorch:latest on a machine with smaller GPU resources
# (see exact values in `apolo config show`) and with two volumes mounted:
#   storage:/<home-directory>   --> /var/storage/home (in read-write mode),
#   storage:/neuromation/public --> /var/storage/neuromation (in read-only mode).
apolo run --preset=gpu-small --volume=storage::/var/storage/home:rw \
--volume=storage:/neuromation/public:/var/storage/home:ro pytorch/pytorch:latest

# Starts a container using the custom image my-ubuntu:latest stored in apolo
# registry, run /script.sh and pass arg1 and arg2 as its arguments:
apolo run -s cpu-small --entrypoint=/script.sh image:my-ubuntu:latest -- arg1 arg2

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--browse_|Open a job's URL in a web browser|
|_--cluster CLUSTER_|Run job in a specified cluster|
|_\-d, --description DESC_|Optional job description in free format|
|_--detach_|Don't attach to job logs and don't wait for exit code|
|_\--energy-schedule NAME_|Run job only within a selected energy schedule. Selected preset should have scheduler enabled.|
|_--entrypoint TEXT_|Executable entrypoint in the container \(note that it overwrites `ENTRYPOINT` and `CMD` instructions of the docker image)|
|_\-e, --env VAR=VAL_|Set environment variable in container. Use multiple options to define more than one variable. See `apolo help secrets` for information about passing secrets as environment variables.|
|_\--env-file PATH_|File with environment variables to pass|
|_\-x, --extshm / -X, --no-extshm_|Request extended '/dev/shm' space  \[default: x]|
|_\--http-auth / --no-http-auth_|Enable HTTP authentication for forwarded HTTP port  \[default: True]|
|_\--http-port PORT_|Enable HTTP port forwarding to container  \[default: 80]|
|_\--life-span TIMEDELTA_|Optional job run-time limit in the format '1d2h3m4s' \(some parts may be missing). Set '0' to disable. Default value '1d' can be changed in the user config.|
|_\-n, --name NAME_|Optional job name|
|_--org ORG_|Run job in a specified org|
|_\--pass-config / --no-pass-config_|Upload apolo config to the job  \[default: no\-pass-config]|
|_\--port-forward LOCAL\_PORT:REMOTE_RORT_|Forward port\(s) of a running job to local port\(s) \(use multiple times for forwarding several ports)|
|_\-s, --preset PRESET_|Predefined resource configuration \(to see available values, run `apolo config show`)|
|_--priority \[low &#124; normal &#124; high]_|Priority used to specify job's start order. Jobs with higher priority will start before ones with lower priority. Priority should be supported by cluster.|
|_--privileged_|Run job in privileged mode, if it is supported by cluster.|
|_\-p, --project PROJECT_|Run job in a specified project.|
|_\--restart \[never &#124; on-failure &#124; always]_|Restart policy to apply when a job exits  \[default: never]|
|_\--schedule-timeout TIMEDELTA_|Optional job schedule timeout in the format '3m4s' \(some parts may be missing).|
|_--share USER_|Share job write permissions to user or role.|
|_--tag TAG_|Optional job tag, multiple values allowed|
|_\-t, --tty / -T, --no-tty_|Allocate a TTY, can be useful for interactive jobs. By default is on if the command is executed from a terminal, non-tty mode is used if executed from a script.|
|_\-v, --volume MOUNT_|Mounts directory from vault into container. Use multiple options to mount more than one volume. See `apolo help secrets` for information about passing secrets as mounted files.|
|_\--wait-for-seat / --no-wait-for-seat_|Wait for total running jobs quota  \[default: no\-wait-for-seat]|
|_\--wait-start / --no-wait-start_|Wait for a job start or failure  \[default: wait-start]|
|_\-w, --workdir TEXT_|Working directory inside the container|




### apolo job save

Save job's state to an image.<br/>

**Usage:**

```bash
apolo job save [OPTIONS] JOB IMAGE
```

**Examples:**

```bash

apolo job save job-id image:ubuntu-patched
apolo job save my-favourite-job image:ubuntu-patched:v1
apolo job save my-favourite-job image://bob/ubuntu-patched

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo job status

Display status of a job.

**Usage:**

```bash
apolo job status [OPTIONS] JOB
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--full-uri_|Output full URI.|




### apolo job top

Display GPU/CPU/Memory usage.<br/>

**Usage:**

```bash
apolo job top [OPTIONS] [JOBS]...
```

**Examples:**

```bash

apolo top
apolo top job-1 job-2
apolo top --owner=user-1 --owner=user-2
apolo top --name my-experiments-v1
apolo top -t tag1 -t tag2

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Show jobs on a specified cluster \(the current cluster by default).|
|_\-d, --description DESCRIPTION_|Filter out jobs by description \(exact match).|
|_--format COLUMNS_|Output table format, see "apolo help top\-format" for more info about the format specification. The default can be changed using the job.top-format configuration variable documented in "apolo help user-config"|
|_\--full-uri_|Output full image URI.|
|_\-n, --name NAME_|Filter out jobs by name.|
|_\-o, --owner TEXT_|Filter out jobs by owner \(multiple option). Supports `ME` option to filter by the current user. Specify `ALL` to show jobs of all users.|
|_\-p, --project PROJECT_|Filter out jobs by project name \(multiple option).|
|_--since DATE\_OR_TIMEDELTA_|Show jobs created after a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|
|_--sort COLUMNS_|Sort rows by specified column. Add "-" prefix to revert the sorting order. Multiple columns can be specified \(comma separated).  \[default: cpu]|
|_\-t, --tag TAG_|Filter out jobs by tag \(multiple option)|
|_--timeout FLOAT_|Maximum allowed time for executing the command, 0 for no timeout  \[default: 0]|
|_--until DATE\_OR_TIMEDELTA_|Show jobs created before a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|




## apolo secret

Operations with secrets.

**Usage:**

```bash
apolo secret [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo secret add](#apolo-secret-add)_| Add secret KEY with data VALUE |
| _[apolo secret ls](#apolo-secret-ls)_| List secrets |
| _[apolo secret rm](#apolo-secret-rm)_| Remove secret KEY |




### apolo secret add

Add secret KEY with data VALUE.<br/><br/>If VALUE starts with @ it points to a file with secrets content.<br/>

**Usage:**

```bash
apolo secret add [OPTIONS] KEY VALUE
```

**Examples:**

```bash

apolo secret add KEY_NAME VALUE
apolo secret add KEY_NAME @path/to/file.txt

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Perform on a specified cluster \(the current cluster by default).|
|_--org ORG_|Look on a specified org \(the current org by default).|
|_--project PROJECT_|Look on a specified project \(the current project by default).|




### apolo secret ls

List secrets.

**Usage:**

```bash
apolo secret ls [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--all-orgs_|Show secrets in all orgs.|
|_\--all-projects_|Show secrets in all projects.|
|_--cluster CLUSTER_|Look on a specified cluster \(the current cluster by default).|
|_\--full-uri_|Output full secret URI.|
|_--org ORG_|Look on a specified org \(the current org by default).|
|_--project PROJECT_|Look on a specified project \(the current project by default).|




### apolo secret rm

Remove secret KEY.

**Usage:**

```bash
apolo secret rm [OPTIONS] KEY
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Perform on a specified cluster \(the current cluster by default).|
|_--org ORG_|Look on a specified org \(the current org by default).|
|_--project PROJECT_|Look on a specified project \(the current project by default).|




## apolo service-account

Operations with service accounts.

**Usage:**

```bash
apolo service-account [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo service-account create](#apolo-service-account-create)_| Create a service account |
| _[apolo service-account get](#apolo-service-account-get)_| Get service account SERVICE_ACCOUNT |
| _[apolo service-account ls](#apolo-service-account-ls)_| List service accounts |
| _[apolo service-account rm](#apolo-service-account-rm)_| Remove service accounts SERVICE_ACCOUNT |




### apolo service-account create

Create a service account.

**Usage:**

```bash
apolo service-account create [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--default-cluster CLUSTER_|Service account default cluster. Current cluster will be used if not specified|
|_\--default-org ORG_|Service account default organization. Current org will be used if not specified|
|_\--default-project PROJECT_|Service account default project. Current project will be used if not specified|
|_--name NAME_|Optional service account name|




### apolo service-account get

Get service account SERVICE_ACCOUNT.

**Usage:**

```bash
apolo service-account get [OPTIONS] SERVICE_ACCOUNT
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo service-account ls

List service accounts.

**Usage:**

```bash
apolo service-account ls [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo service-account rm

Remove service accounts SERVICE_ACCOUNT.

**Usage:**

```bash
apolo service-account rm [OPTIONS] SERVICE_ACCOUNTS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo storage

Storage operations.

**Usage:**

```bash
apolo storage [OPTIONS] COMMAND [ARGS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|


**Commands:**

|Usage|Description|
|---|---|
| _[apolo storage cp](#apolo-storage-cp)_| Copy files and directories |
| _[apolo storage df](#apolo-storage-df)_| Show current storage usage |
| _[apolo storage glob](#apolo-storage-glob)_| List resources that match PATTERNS |
| _[apolo storage ls](#apolo-storage-ls)_| List directory contents |
| _[apolo storage mkdir](#apolo-storage-mkdir)_| Make directories |
| _[apolo storage mv](#apolo-storage-mv)_| Move or rename files and directories |
| _[apolo storage rm](#apolo-storage-rm)_| Remove files or directories |
| _[apolo storage tree](#apolo-storage-tree)_| List storage in a tree-like format |




### apolo storage cp

Copy files and directories.<br/><br/>Either SOURCES or DESTINATION should have storage:// scheme. If scheme is<br/>omitted, file:// scheme is assumed.<br/><br/>Use /dev/stdin and /dev/stdout file names to copy a file from terminal and<br/>print the content of file on the storage to console.<br/><br/>Any number of \--exclude and --include options can be passed.  The filters that<br/>appear later in the command take precedence over filters that appear earlier<br/>in the command.  If neither \--exclude nor --include options are specified the<br/>default can be changed using the storage.cp-exclude configuration variable<br/>documented in "apolo help user-config".<br/>

**Usage:**

```bash
apolo storage cp [OPTIONS] [SOURCES]... [DESTINATION]
```

**Examples:**

```bash

# copy local files into remote storage root
apolo cp foo.txt bar/baz.dat storage:
apolo cp foo.txt bar/baz.dat -t storage:

# copy local directory `foo` into existing remote directory `bar`
apolo cp -r foo -t storage:bar

# copy the content of local directory `foo` into existing remote
# directory `bar`
apolo cp -r -T storage:foo storage:bar

# download remote file `foo.txt` into local file `/tmp/foo.txt` with
# explicit file:// scheme set
apolo cp storage:foo.txt file:///tmp/foo.txt
apolo cp -T storage:foo.txt file:///tmp/foo.txt
apolo cp storage:foo.txt file:///tmp
apolo cp storage:foo.txt -t file:///tmp

# download other project's remote file into the current directory
apolo cp storage:/{project}/foo.txt .

# download only files with extension `.out` into the current directory
apolo cp storage:results/*.out .

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--continue_|Continue copying partially-copied files.|
|_\--exclude-from-files FILES_|A list of file names that contain patterns for exclusion files and directories. Used only for uploading. The default can be changed using the storage.cp\-exclude-from-files configuration variable documented in "apolo help user-config"|
|_--exclude TEXT_|Exclude files and directories that match the specified pattern.|
|_--include TEXT_|Don't exclude files and directories that match the specified pattern.|
|_\--glob / --no-glob_|Expand glob patterns in SOURCES with explicit scheme.  \[default: glob]|
|_\-T, --no-target-directory_|Treat DESTINATION as a normal file.|
|_\-p, --progress / -P, --no-progress_|Show progress, on by default in TTY mode, off otherwise.|
|_\-r, --recursive_|Recursive copy, off by default|
|_\-t, --target-directory DIRECTORY_|Copy all SOURCES into DIRECTORY.|
|_\-u, --update_|Copy only when the SOURCE file is newer than the destination file or when the destination file is missing.|




### apolo storage df

Show current storage usage.<br/><br/>If PATH is specified, show storage usage of which path is a part.

**Usage:**

```bash
apolo storage df [OPTIONS] [PATH]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo storage glob

List resources that match PATTERNS.

**Usage:**

```bash
apolo storage glob [OPTIONS] [PATTERNS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




### apolo storage ls

List directory contents.<br/><br/>By default PATH is equal project's dir \(storage:)

**Usage:**

```bash
apolo storage ls [OPTIONS] [PATHS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-d, --directory_|list directories themselves, not their contents.|
|_-l_|use a long listing format.|
|_\-h, --human-readable_|with -l print human readable sizes \(e.g., 2K, 540M).|
|_\-a, --all_|do not ignore entries starting with .|
|_--sort \[name &#124; size &#124; time]_|sort by given field, default is name.|




### apolo storage mkdir

Make directories.

**Usage:**

```bash
apolo storage mkdir [OPTIONS] PATHS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-p, --parents_|No error if existing, make parent directories as needed|




### apolo storage mv

Move or rename files and directories.<br/><br/>SOURCE must contain path to the file or directory existing on the storage, and<br/>DESTINATION must contain the full path to the target file or directory.<br/>

**Usage:**

```bash
apolo storage mv [OPTIONS] [SOURCES]... [DESTINATION]
```

**Examples:**

```bash

# move and rename remote file
apolo mv storage:foo.txt storage:bar/baz.dat
apolo mv -T storage:foo.txt storage:bar/baz.dat

# move remote files into existing remote directory
apolo mv storage:foo.txt storage:bar/baz.dat storage:dst
apolo mv storage:foo.txt storage:bar/baz.dat -t storage:dst

# move the content of remote directory into other existing
# remote directory
apolo mv -T storage:foo storage:bar

# move remote file into other project's directory
apolo mv storage:foo.txt storage:/{project}/bar.dat

# move remote file from other project's directory
apolo mv storage:/{project}/foo.txt storage:bar.dat

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--glob / --no-glob_|Expand glob patterns in SOURCES  \[default: glob]|
|_\-T, --no-target-directory_|Treat DESTINATION as a normal file|
|_\-t, --target-directory DIRECTORY_|Copy all SOURCES into DIRECTORY|




### apolo storage rm

Remove files or directories.<br/>

**Usage:**

```bash
apolo storage rm [OPTIONS] PATHS...
```

**Examples:**

```bash

apolo rm storage:foo/bar
apolo rm storage:/{project}/foo/bar
apolo rm storage://{cluster}/{project}/foo/bar
apolo rm --recursive storage:/{project}/foo/
apolo rm storage:foo/**/*.tmp

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--glob / --no-glob_|Expand glob patterns in PATHS  \[default: glob]|
|_\-p, --progress / -P, --no-progress_|Show progress, on by default in TTY mode, off otherwise.|
|_\-r, --recursive_|remove directories and their contents recursively|




### apolo storage tree

List storage in a tree-like format<br/><br/>Tree is a recursive directory listing program that produces a depth indented<br/>listing of files, which is colorized ala dircolors if the LS_COLORS<br/>environment variable is set and output is to tty.  With no arguments, tree<br/>lists the files in the storage: directory.  When directory arguments are<br/>given, tree lists all the files and/or directories found in the given<br/>directories each in turn.  Upon completion of listing all files/directories<br/>found, tree returns the total number of files and/or directories listed.<br/><br/>By default PATH is equal project's dir \(storage:)

**Usage:**

```bash
apolo storage tree [OPTIONS] [PATH]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-h, --human-readable_|Print the size in a more human readable way.|
|_\-a, --all_|do not ignore entries starting with .|
|_\-s, --size_|Print the size in bytes of each file.|
|_--sort \[name &#124; size &#124; time]_|sort by given field, default is name|




## apolo attach

Attach terminal to a job<br/><br/>Attach local standard input, output, and error streams to a running job.

**Usage:**

```bash
apolo attach [OPTIONS] JOB
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--port-forward LOCAL\_PORT:REMOTE_RORT_|Forward port\(s) of a running job to local port\(s) \(use multiple times for forwarding several ports)|




## apolo cp

Copy files and directories.<br/><br/>Either SOURCES or DESTINATION should have storage:// scheme. If scheme is<br/>omitted, file:// scheme is assumed.<br/><br/>Use /dev/stdin and /dev/stdout file names to copy a file from terminal and<br/>print the content of file on the storage to console.<br/><br/>Any number of \--exclude and --include options can be passed.  The filters that<br/>appear later in the command take precedence over filters that appear earlier<br/>in the command.  If neither \--exclude nor --include options are specified the<br/>default can be changed using the storage.cp-exclude configuration variable<br/>documented in "apolo help user-config".<br/>

**Usage:**

```bash
apolo cp [OPTIONS] [SOURCES]... [DESTINATION]
```

**Examples:**

```bash

# copy local files into remote storage root
apolo cp foo.txt bar/baz.dat storage:
apolo cp foo.txt bar/baz.dat -t storage:

# copy local directory `foo` into existing remote directory `bar`
apolo cp -r foo -t storage:bar

# copy the content of local directory `foo` into existing remote
# directory `bar`
apolo cp -r -T storage:foo storage:bar

# download remote file `foo.txt` into local file `/tmp/foo.txt` with
# explicit file:// scheme set
apolo cp storage:foo.txt file:///tmp/foo.txt
apolo cp -T storage:foo.txt file:///tmp/foo.txt
apolo cp storage:foo.txt file:///tmp
apolo cp storage:foo.txt -t file:///tmp

# download other project's remote file into the current directory
apolo cp storage:/{project}/foo.txt .

# download only files with extension `.out` into the current directory
apolo cp storage:results/*.out .

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--continue_|Continue copying partially-copied files.|
|_\--exclude-from-files FILES_|A list of file names that contain patterns for exclusion files and directories. Used only for uploading. The default can be changed using the storage.cp\-exclude-from-files configuration variable documented in "apolo help user-config"|
|_--exclude TEXT_|Exclude files and directories that match the specified pattern.|
|_--include TEXT_|Don't exclude files and directories that match the specified pattern.|
|_\--glob / --no-glob_|Expand glob patterns in SOURCES with explicit scheme.  \[default: glob]|
|_\-T, --no-target-directory_|Treat DESTINATION as a normal file.|
|_\-p, --progress / -P, --no-progress_|Show progress, on by default in TTY mode, off otherwise.|
|_\-r, --recursive_|Recursive copy, off by default|
|_\-t, --target-directory DIRECTORY_|Copy all SOURCES into DIRECTORY.|
|_\-u, --update_|Copy only when the SOURCE file is newer than the destination file or when the destination file is missing.|




## apolo exec

Execute command in a running job.<br/>

**Usage:**

```bash
apolo exec [OPTIONS] JOB -- CMD...
```

**Examples:**

```bash

# Provides a shell to the container:
apolo exec my-job -- /bin/bash

# Executes a single command in the container and returns the control:
apolo exec --no-tty my-job -- ls -l

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-t, --tty / -T, --no-tty_|Allocate a TTY, can be useful for interactive jobs. By default is on if the command is executed from a terminal, non-tty mode is used if executed from a script.|




## apolo help

Get help on a command.

**Usage:**

```bash
apolo help [OPTIONS] [COMMAND]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo images

List images.

**Usage:**

```bash
apolo images [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--all-orgs_|Show images in all orgs.|
|_\--all-projects_|Show images in all projects.|
|_--cluster CLUSTER_|Show images on a specified cluster \(the current cluster by default).|
|_-l_|List in long format.|
|_\--full-uri_|Output full image URI.|
|_\-n, --name PATTERN_|Filter out images by name regex.|
|_--org ORG_|Filter out images by org \(multiple option, the current org by default).|
|_--project PROJECT_|Filter out images by project \(multiple option, the current project by default).|




## apolo kill

Kill job\(s).

**Usage:**

```bash
apolo kill [OPTIONS] JOBS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo login

Log into Apolo Platform.<br/><br/>URL is a platform entrypoint URL.

**Usage:**

```bash
apolo login [OPTIONS] [URL]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo logout

Log out.

**Usage:**

```bash
apolo logout [OPTIONS]
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo logs

Print the logs for a job.

**Usage:**

```bash
apolo logs [OPTIONS] JOB
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--since DATE\_OR_TIMEDELTA_|Only return logs after a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|
|_--timestamps_|Include timestamps on each line in the log output.|




## apolo ls

List directory contents.<br/><br/>By default PATH is equal project's dir \(storage:)

**Usage:**

```bash
apolo ls [OPTIONS] [PATHS]...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-d, --directory_|list directories themselves, not their contents.|
|_-l_|use a long listing format.|
|_\-h, --human-readable_|with -l print human readable sizes \(e.g., 2K, 540M).|
|_\-a, --all_|do not ignore entries starting with .|
|_--sort \[name &#124; size &#124; time]_|sort by given field, default is name.|




## apolo mkdir

Make directories.

**Usage:**

```bash
apolo mkdir [OPTIONS] PATHS...
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-p, --parents_|No error if existing, make parent directories as needed|




## apolo mv

Move or rename files and directories.<br/><br/>SOURCE must contain path to the file or directory existing on the storage, and<br/>DESTINATION must contain the full path to the target file or directory.<br/>

**Usage:**

```bash
apolo mv [OPTIONS] [SOURCES]... [DESTINATION]
```

**Examples:**

```bash

# move and rename remote file
apolo mv storage:foo.txt storage:bar/baz.dat
apolo mv -T storage:foo.txt storage:bar/baz.dat

# move remote files into existing remote directory
apolo mv storage:foo.txt storage:bar/baz.dat storage:dst
apolo mv storage:foo.txt storage:bar/baz.dat -t storage:dst

# move the content of remote directory into other existing
# remote directory
apolo mv -T storage:foo storage:bar

# move remote file into other project's directory
apolo mv storage:foo.txt storage:/{project}/bar.dat

# move remote file from other project's directory
apolo mv storage:/{project}/foo.txt storage:bar.dat

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--glob / --no-glob_|Expand glob patterns in SOURCES  \[default: glob]|
|_\-T, --no-target-directory_|Treat DESTINATION as a normal file|
|_\-t, --target-directory DIRECTORY_|Copy all SOURCES into DIRECTORY|




## apolo port-forward

Forward port\(s) of a job.<br/><br/>Forwards port\(s) of a running job to local port\(s).<br/>

**Usage:**

```bash
apolo port-forward [OPTIONS] JOB LOCAL_PORT:REMOTE_RORT...
```

**Examples:**

```bash

# Forward local port 2080 to port 80 of job's container.
# You can use http://localhost:2080 in browser to access job's served http
apolo job port-forward my-fastai-job 2080:80

# Forward local port 2222 to job's port 22
# Then copy all data from container's folder '/data' to current folder
# (please run second command in other terminal)
apolo job port-forward my-job-with-ssh-server 2222:22
rsync -avxzhe ssh -p 2222 root@localhost:/data .

# Forward few ports at once
apolo job port-forward my-job 2080:80 2222:22 2000:100

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo ps

List all jobs.<br/>

**Usage:**

```bash
apolo ps [OPTIONS]
```

**Examples:**

```bash

apolo ps -a
apolo ps -a --owner=user-1 --owner=user-2
apolo ps --name my-experiments-v1 -s failed -s succeeded
apolo ps --description=my favourite job
apolo ps -s failed -s succeeded -q
apolo ps -t tag1 -t tag2

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\-a, --all_|Show all jobs regardless the status.|
|_\--all-orgs_|Show jobs in all orgs.|
|_\--all-projects_|Show jobs in all projects.|
|_--cluster CLUSTER_|Show jobs on a specified cluster \(the current cluster by default).|
|_\-d, --description DESCRIPTION_|Filter out jobs by description \(exact match).|
|_--distinct_|Show only first job if names are same.|
|_--format COLUMNS_|Output table format, see "apolo help ps\-format" for more info about the format specification. The default can be changed using the job.ps-format configuration variable documented in "apolo help user-config"|
|_\--full-uri_|Output full image URI.|
|_\-n, --name NAME_|Filter out jobs by name.|
|_--org ORG_|Filter out jobs by org name \(multiple option, the current org by default).|
|_\-o, --owner TEXT_|Filter out jobs by owner \(multiple option). Supports `ME` option to filter by the current user.|
|_\-p, --project PROJECT_|Filter out jobs by project name \(multiple option, the current project by default).|
|_\--recent-first / --recent-last_|Show newer jobs first or last|
|_--since DATE\_OR_TIMEDELTA_|Show jobs created after a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|
|_\-s, --status \[pending &#124; suspended &#124; running &#124; succeeded &#124; failed &#124; cancelled]_|Filter out jobs by status \(multiple option).|
|_\-t, --tag TAG_|Filter out jobs by tag \(multiple option)|
|_--until DATE\_OR_TIMEDELTA_|Show jobs created before a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|
|_\-w, --wide_|Do not cut long lines for terminal width.|




## apolo pull

Pull an image from platform registry.<br/><br/>Remote image name must be URL with image:// scheme. Image names can contain<br/>tag.<br/>

**Usage:**

```bash
apolo pull [OPTIONS] REMOTE_IMAGE [LOCAL_IMAGE]
```

**Examples:**

```bash

apolo pull image:myimage
apolo pull image:/other-project/alpine:shared
apolo pull image:/project/my-alpine:production alpine:from-registry

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo push

Push an image to platform registry.<br/><br/>Remote image must be URL with image:// scheme. Image names can contain tag. If<br/>tags not specified 'latest' will be used as value.<br/>

**Usage:**

```bash
apolo push [OPTIONS] LOCAL_IMAGE [REMOTE_IMAGE]
```

**Examples:**

```bash

apolo push myimage
apolo push alpine:latest image:my-alpine:production
apolo push alpine image:/other-project/alpine:shared

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo rm

Remove files or directories.<br/>

**Usage:**

```bash
apolo rm [OPTIONS] PATHS...
```

**Examples:**

```bash

apolo rm storage:foo/bar
apolo rm storage:/{project}/foo/bar
apolo rm storage://{cluster}/{project}/foo/bar
apolo rm --recursive storage:/{project}/foo/
apolo rm storage:foo/**/*.tmp

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--glob / --no-glob_|Expand glob patterns in PATHS  \[default: glob]|
|_\-p, --progress / -P, --no-progress_|Show progress, on by default in TTY mode, off otherwise.|
|_\-r, --recursive_|remove directories and their contents recursively|




## apolo run

Run a job<br/><br/>IMAGE docker image name to run in a job.<br/><br/>CMD list will be passed as arguments to the executed job's image.<br/>

**Usage:**

```bash
apolo run [OPTIONS] IMAGE [-- CMD...]
```

**Examples:**

```bash

# Starts a container pytorch/pytorch:latest on a machine with smaller GPU resources
# (see exact values in `apolo config show`) and with two volumes mounted:
#   storage:/<home-directory>   --> /var/storage/home (in read-write mode),
#   storage:/neuromation/public --> /var/storage/neuromation (in read-only mode).
apolo run --preset=gpu-small --volume=storage::/var/storage/home:rw \
--volume=storage:/neuromation/public:/var/storage/home:ro pytorch/pytorch:latest

# Starts a container using the custom image my-ubuntu:latest stored in apolo
# registry, run /script.sh and pass arg1 and arg2 as its arguments:
apolo run -s cpu-small --entrypoint=/script.sh image:my-ubuntu:latest -- arg1 arg2

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--browse_|Open a job's URL in a web browser|
|_--cluster CLUSTER_|Run job in a specified cluster|
|_\-d, --description DESC_|Optional job description in free format|
|_--detach_|Don't attach to job logs and don't wait for exit code|
|_\--energy-schedule NAME_|Run job only within a selected energy schedule. Selected preset should have scheduler enabled.|
|_--entrypoint TEXT_|Executable entrypoint in the container \(note that it overwrites `ENTRYPOINT` and `CMD` instructions of the docker image)|
|_\-e, --env VAR=VAL_|Set environment variable in container. Use multiple options to define more than one variable. See `apolo help secrets` for information about passing secrets as environment variables.|
|_\--env-file PATH_|File with environment variables to pass|
|_\-x, --extshm / -X, --no-extshm_|Request extended '/dev/shm' space  \[default: x]|
|_\--http-auth / --no-http-auth_|Enable HTTP authentication for forwarded HTTP port  \[default: True]|
|_\--http-port PORT_|Enable HTTP port forwarding to container  \[default: 80]|
|_\--life-span TIMEDELTA_|Optional job run-time limit in the format '1d2h3m4s' \(some parts may be missing). Set '0' to disable. Default value '1d' can be changed in the user config.|
|_\-n, --name NAME_|Optional job name|
|_--org ORG_|Run job in a specified org|
|_\--pass-config / --no-pass-config_|Upload apolo config to the job  \[default: no\-pass-config]|
|_\--port-forward LOCAL\_PORT:REMOTE_RORT_|Forward port\(s) of a running job to local port\(s) \(use multiple times for forwarding several ports)|
|_\-s, --preset PRESET_|Predefined resource configuration \(to see available values, run `apolo config show`)|
|_--priority \[low &#124; normal &#124; high]_|Priority used to specify job's start order. Jobs with higher priority will start before ones with lower priority. Priority should be supported by cluster.|
|_--privileged_|Run job in privileged mode, if it is supported by cluster.|
|_\-p, --project PROJECT_|Run job in a specified project.|
|_\--restart \[never &#124; on-failure &#124; always]_|Restart policy to apply when a job exits  \[default: never]|
|_\--schedule-timeout TIMEDELTA_|Optional job schedule timeout in the format '3m4s' \(some parts may be missing).|
|_--share USER_|Share job write permissions to user or role.|
|_--tag TAG_|Optional job tag, multiple values allowed|
|_\-t, --tty / -T, --no-tty_|Allocate a TTY, can be useful for interactive jobs. By default is on if the command is executed from a terminal, non-tty mode is used if executed from a script.|
|_\-v, --volume MOUNT_|Mounts directory from vault into container. Use multiple options to mount more than one volume. See `apolo help secrets` for information about passing secrets as mounted files.|
|_\--wait-for-seat / --no-wait-for-seat_|Wait for total running jobs quota  \[default: no\-wait-for-seat]|
|_\--wait-start / --no-wait-start_|Wait for a job start or failure  \[default: wait-start]|
|_\-w, --workdir TEXT_|Working directory inside the container|




## apolo save

Save job's state to an image.<br/>

**Usage:**

```bash
apolo save [OPTIONS] JOB IMAGE
```

**Examples:**

```bash

apolo job save job-id image:ubuntu-patched
apolo job save my-favourite-job image:ubuntu-patched:v1
apolo job save my-favourite-job image://bob/ubuntu-patched

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo share

Shares resource with another user.<br/><br/>URI shared resource.<br/><br/>USER username to share resource with.<br/><br/>PERMISSION sharing access right: read, write, or manage.<br/>

**Usage:**

```bash
apolo share [OPTIONS] URI USER {read|write|manage}
```

**Examples:**

```bash

apolo acl grant storage:///sample_data/ alice manage
apolo acl grant image:resnet50 bob read
apolo acl grant job:///my_job_id alice write

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|




## apolo status

Display status of a job.

**Usage:**

```bash
apolo status [OPTIONS] JOB
```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_\--full-uri_|Output full URI.|




## apolo top

Display GPU/CPU/Memory usage.<br/>

**Usage:**

```bash
apolo top [OPTIONS] [JOBS]...
```

**Examples:**

```bash

apolo top
apolo top job-1 job-2
apolo top --owner=user-1 --owner=user-2
apolo top --name my-experiments-v1
apolo top -t tag1 -t tag2

```

**Options:**

Name | Description|
|----|------------|
|_--help_|Show this message and exit.|
|_--cluster CLUSTER_|Show jobs on a specified cluster \(the current cluster by default).|
|_\-d, --description DESCRIPTION_|Filter out jobs by description \(exact match).|
|_--format COLUMNS_|Output table format, see "apolo help top\-format" for more info about the format specification. The default can be changed using the job.top-format configuration variable documented in "apolo help user-config"|
|_\--full-uri_|Output full image URI.|
|_\-n, --name NAME_|Filter out jobs by name.|
|_\-o, --owner TEXT_|Filter out jobs by owner \(multiple option). Supports `ME` option to filter by the current user. Specify `ALL` to show jobs of all users.|
|_\-p, --project PROJECT_|Filter out jobs by project name \(multiple option).|
|_--since DATE\_OR_TIMEDELTA_|Show jobs created after a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|
|_--sort COLUMNS_|Sort rows by specified column. Add "-" prefix to revert the sorting order. Multiple columns can be specified \(comma separated).  \[default: cpu]|
|_\-t, --tag TAG_|Filter out jobs by tag \(multiple option)|
|_--timeout FLOAT_|Maximum allowed time for executing the command, 0 for no timeout  \[default: 0]|
|_--until DATE\_OR_TIMEDELTA_|Show jobs created before a specific date \(including). Use value of format '1d2h3m4s' to specify moment in past relatively to current time.|


