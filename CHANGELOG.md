[comment]: # (Please do not modify this file)
[comment]: # (Put you comments to changelog.d and it will be moved to changelog in next release)

[comment]: # (Clear the text on make release for canceling the release)

[comment]: # (towncrier release notes start)

# Apolo SDK/CLI 25.5.0 (2025-05-15)

### Features

- Added new command `apolo app logs [id]` - view logs from a running app ([#3249](https://github.com/neuro-inc/neuro-cli/issues/3249))


# Apolo SDK/CLI 25.4.2 (2025-04-30)

### Features

- Added new command `apolo app-template ls` - list available app templates for installation ([#3227](https://github.com/neuro-inc/neuro-cli/issues/3227))
- Added new command `apolo app-template ls-versions` - list available app templates for specific versions ([#3228](https://github.com/neuro-inc/neuro-cli/issues/3228))
- Added new aliases for: `apolo app list|ls`, `apolo app-template list|ls`, `apolo app-template list-versions|ls-versions` ([#3233](https://github.com/neuro-inc/neuro-cli/issues/3233))
- Added new command `apolo app get-values` - list available values that can be reused for installation ([#3236](https://github.com/neuro-inc/neuro-cli/issues/3236))


# Apolo SDK/CLI 25.4.1 (2025-04-01)

### Features

- Added new command: `apolo app ls` - list installed apps ([#3199](https://github.com/neuro-inc/neuro-cli/issues/3199))
- Added new command: `apolo app uninstall` - uninstall app ([#3201](https://github.com/neuro-inc/neuro-cli/issues/3201))
- Added new command: `apolo app install -f [yml_file]` - install app ([#3204](https://github.com/neuro-inc/neuro-cli/issues/3204))

### Bugfixes

- Eliminated backtracing in regexes for job, disk, and bucket name validators. ([#3217](https://github.com/neuro-inc/neuro-cli/issues/3217))


# Apolo SDK/CLI 24.12.3 (2024-12-19)

### Bugfixes

- Fix S3 acceess by dropping aiobotocore patching and using public API instead. ([#3155](https://github.com/neuro-inc/neuro-cli/issues/3155))


# Apolo SDK/CLI 24.12.2 (2024-12-18)

No significant changes.


# Apolo SDK/CLI 24.12.1 (2024-12-16)

### Features

- Added cluster-bound apps configuration into the SDK. ([#3142](https://github.com/neuro-inc/neuro-cli/issues/3142))
- Prefer `.apolo` configuration folder and `.apoloignore` files and folders over old `.neuro` based names; old names are still supported. ([#3145](https://github.com/neuro-inc/neuro-cli/issues/3145))
- Balance is no longer stored on a cluster level, and was moved to an organization level, e.g.,
  to an org itself, and to an org users, instead of a cluster / cluster users.

  New commands:
	- `apolo admin set-org-defaults` - allows to set an organization default values, such as a default user credits

  Existing commands changes:
	- `apolo admin add-cluster-user` cmd is no longer accepting a `credits` argument.
	- `apolo admin set-user-credits` cmd is now expecting an org name instead of a cluster name.
	- `apolo admin add-user-credits` cmd is now expecting an org name instead of a cluster name.
	- `apolo admin set-org-cluster-credits` was removed in a favor of an `apolo admin set-org-credits`.
	- `apolo admin add-org-cluster-credits` was removed in a favor of an `apolo admin add-org-credits`. ([#3137](https://github.com/neuro-inc/neuro-cli/issues/3137))

### Bugfixes

- Stop using deprecated `ssl.PROTOCOL_TLS` in favor of `ssl.PROTOCOL_TLS_CLIENT` ([#3146](https://github.com/neuro-inc/neuro-cli/issues/3146))


# Apolo SDK/CLI 24.11.4 (2024-11-22)

No significant changes.


# Apolo SDK/CLI 24.11.3 (2024-11-22)

No significant changes.


# Apolo SDK/CLI 24.11.2 (2024-11-22)

No significant changes.


# Apolo SDK/CLI 24.11.1 (2024-11-21)

No significant changes.


# Apolo SDK/CLI 24.11.0 (2024-11-07)

No significant changes.


# Apolo SDK/CLI 24.8.1 (2024-09-18)

No significant changes.


Apolo SDK/CLI 24.8.1 (2024-08-08)
=================================

No significant changes.


Apolo SDK/CLI 24.8.0 (2024-08-08)
=================================

Misc
----

- [#3034](https://github.com/neuro-inc/neuro-cli/issues/3034)


Apolo SDK/CLI 24.7.1 (2024-07-19)
=================================

No significant changes.


Apolo SDK/CLI 24.7.0 (2024-07-19)
=================================

Features
--------

- Add update-cluster-user command. ([#3009](https://github.com/neuro-inc/neuro-cli/issues/3009))
- Rename neuro-cli/neuro-sdk to apolo-cli/apolo-sdk ([#3010](https://github.com/neuro-inc/neuro-cli/pull/3010))


Neuro SDK/CLI 24.5.0 (2024-05-21)
=================================

Features
--------

- Support AMD, Intel GPUs ([#3007](https://github.com/neuro-inc/neuro-cli/issues/3007))


Neuro SDK/CLI 24.2.0 (2024-02-12)
=================================

No significant changes.


Neuro SDK/CLI 24.1.0 (2024-01-02)
=================================

Bugfixes
--------

- Do not perform terminal settings reset in PyCharm while it causes screen cleanup. ([#3005](https://github.com/neuro-inc/neuro-cli/issues/3005))


Neuro SDK/CLI 23.11.0 (2023-11-14)
==================================

No significant changes.


Neuro SDK/CLI 23.10.0 (2023-10-26)
==================================

No significant changes.


Neuro SDK/CLI 23.7.0 (2023-07-03)
=================================

Features
--------

- Commands `neuro run`, `neuro logs`, `neuro attach` and `neuro exec` in non-quiet mode now prints details for cancelled and failed jobs. Also improved other indications of the job status. ([#2800](https://github.com/neuro-inc/platform-client-python/issues/2800))
- Commands `neuro run` and `neuro attach` now re-attach to restarted jobs. Previously they waited until the job finished. ([#2802](https://github.com/neuro-inc/platform-client-python/issues/2802))
- Added support of cluster energy schedules.
  `neuro config show --energy` will display awailable energy schedule periods.
  `neuro run --schedule-name <energy-schedule-name>` will run the job within the specified <energy-schedule-name>. Note - the selected preset should have an enabled scheduler.
  `neuro status <job-id>` will include the energy schedule name if one was used for running the job. ([#2903](https://github.com/neuro-inc/platform-client-python/issues/2903))
- Added Python 3.11 support. ([#2908](https://github.com/neuro-inc/platform-client-python/issues/2908))
- Add `neuro config switch-project` command. ([#2940](https://github.com/neuro-inc/platform-client-python/issues/2940))
- Support projects in storage commands, make project directory default instead of user home directory. ([#2949](https://github.com/neuro-inc/platform-client-python/issues/2949))
- Support projects in image commands. ([#2950](https://github.com/neuro-inc/platform-client-python/issues/2950))
- Support projects in `neuro secret` cli. ([#2952](https://github.com/neuro-inc/platform-client-python/issues/2952))
- Support projects in `neuro blob` cli commands and `neuro-sdk`. ([#2954](https://github.com/neuro-inc/platform-client-python/issues/2954))
- Add project support in `neuro job` commands. ([#2955](https://github.com/neuro-inc/platform-client-python/issues/2955))
- Support projects in disk CLI commands and SDK methods. ([#2960](https://github.com/neuro-inc/platform-client-python/issues/2960))
- Support projects in service account CLI commands and SDK methods. ([#2965](https://github.com/neuro-inc/platform-client-python/issues/2965))
- Unhide remove-project command. ([#2976](https://github.com/neuro-inc/platform-client-python/issues/2976))
- Align all `ls` command options. ([#2995](https://github.com/neuro-inc/platform-client-python/issues/2995))


Bugfixes
--------

- Fix human-readable datetime formatter to correctly report jobs lifespan ending in future ([#2933](https://github.com/neuro-inc/platform-client-python/issues/2933))
- Update projects after fetching config from server. ([#2992](https://github.com/neuro-inc/platform-client-python/issues/2992))


Neuro SDK/CLI 22.7.1 (2022-07-27)
=================================

Features
--------

- Add update-node-pool command. Only idle_size update is available. ([#2740](https://github.com/neuro-inc/platform-client-python/issues/2740))
- Integrate neuro-config-client package. ([#2791](https://github.com/neuro-inc/platform-client-python/issues/2791))
- Added project management commands to `neuro admin`. ([#2798](https://github.com/neuro-inc/platform-client-python/issues/2798))


Bugfixes
--------

- Fix `neuro admin update-resource-preset`: previous values are now used for boolean parameters if options `--scheduler/--no-scheduler` or `--preemptible-node/--no-preemptible-node` are not explicitly specified. ([#2761](https://github.com/neuro-inc/platform-client-python/issues/2761))


Neuro SDK/CLI 22.7.0 (2022-07-04)
=================================

Features
--------

- Update size formatting: use decimal prefixes ([#2768](https://github.com/neuro-inc/platform-client-python/issues/2768))


Bugfixes
--------

- Fix formatting URIs in short form for users with organization. ([#2749](https://github.com/neuro-inc/platform-client-python/issues/2749))
- Disks, buckets and secrets are now created with the current organization instead of no organization if `--org` is not explicitly specified. ([#2756](https://github.com/neuro-inc/platform-client-python/issues/2756))


Misc
----

- [#2752](https://github.com/neuro-inc/platform-client-python/issues/2752)


Neuro SDK/CLI 22.6.3 (2022-06-30)
=================================

Bugfixes
--------

- Pin `neuro-admin-client` to `>=22.6.4`, make SDK future-compatible with next `neuro-admin-client` releases. ([#2757](https://github.com/neuro-inc/platform-client-python/issues/2757))


Neuro SDK/CLI 22.6.2 (2022-06-15)
=================================

Features
--------

- Allow user without clusters call neuro-sdk Jobs.status method if they have permissions. ([#2733](https://github.com/neuro-inc/platform-client-python/issues/2733))


Neuro SDK/CLI 22.6.1 (2022-06-09)
=================================

Features
--------

- Re-load clusters config in `neuro config show`. ([#2728](https://github.com/neuro-inc/platform-client-python/issues/2728))


Neuro SDK/CLI 22.6.0 (2022-06-07)
=================================

Features
--------

- Support organization storage in disk usage command when user switches to organization. ([#2585](https://github.com/neuro-inc/platform-client-python/issues/2585))
- Added `neuro admin set-org-cluster-defaults` command to allow org cluster manager to modify org cluster defaults. ([#2602](https://github.com/neuro-inc/platform-client-python/issues/2602))
- Support custom storage path in disk usage command. ([#2622](https://github.com/neuro-inc/platform-client-python/issues/2622))
- `neuro blob statbucket` now displays some additional information
  for imported buckets.

  * For AWS: "External name", "External endpoint", "External region name".
  * For Azure: "External name", "External endpoint".
  * For GCP: "External name". ([#2706](https://github.com/neuro-inc/platform-client-python/issues/2706))


Bugfixes
--------

- Fix resolving job URIs containing organization name and/or service account name. ([#2572](https://github.com/neuro-inc/platform-client-python/issues/2572))
- Provide click 8.1.3 support with keeping 8.0+ compatibility. ([#2689](https://github.com/neuro-inc/platform-client-python/issues/2689))


Misc
----

- [#2568](https://github.com/neuro-inc/platform-client-python/issues/2568), [#2569](https://github.com/neuro-inc/platform-client-python/issues/2569), [#2601](https://github.com/neuro-inc/platform-client-python/issues/2601)


Neuro SDK/CLI 22.1.3 (2022-01-27)
=================================

Features
--------

- Support organization storage size parameter. ([#2560](https://github.com/neuro-inc/platform-client-python/issues/2560))


Neuro SDK/CLI 22.1.2 (2022-01-25)
=================================

Features
--------

- Added client-side validation of docker image name and tag. ([#2525](https://github.com/neuro-inc/platform-client-python/issues/2525))
- Added support of column type `org_name` to ps-format. ([#2533](https://github.com/neuro-inc/platform-client-python/issues/2533))
- Added "ORG" column to get-cluster-users output. ([#2541](https://github.com/neuro-inc/platform-client-python/issues/2541))
- Added info about org quota to `neuro config show`. ([#2545](https://github.com/neuro-inc/platform-client-python/issues/2545))


Bugfixes
--------

- Cluster/org name validness now checked after config re-fetch in `neuro config switch-cluster`
  and `neuro config switch-org` commands. ([#2543](https://github.com/neuro-inc/platform-client-python/issues/2543))


Neuro SDK/CLI 22.1.1 (2022-01-18)
=================================

Features
--------

- Add command `neuro acl list-roles` to list roles created by user. ([#2496](https://github.com/neuro-inc/platform-client-python/issues/2496))
- Added support to set/update cluster level default credits and quota.

  Use options `--default-credits` and `--default-jobs` of commands `neuro admin add-cluster`,
  `neuro admin update-cluster`, `neuro admin add-org-cluster` and `neuro admin update-org-cluster`
  to set and update cluster defaults. This values will when new user with role "user" is added to cluster
  (either by `neuro admin add-cluster-user` or if user registers himself using web interface).
  The default for managers and admins is unlimited quota and credits as the can edit their quota.

  You can override default value by using `--credits` and `--jobs` options of
  `neuro admin add-org-cluster` command. ([#2520](https://github.com/neuro-inc/platform-client-python/issues/2520))


Bugfixes
--------

- Fixed memory leak in `neuro blob cp`. ([#2523](https://github.com/neuro-inc/platform-client-python/issues/2523))


Neuro SDK/CLI 22.1.0 (2022-01-10)
=================================

Features
--------

- Added support `--owner` argument in blob bucket level commands to allow referring to another users bucket by name. ([#2494](https://github.com/neuro-inc/platform-client-python/issues/2494))
- Add --force/-f flag to neuro blob rmbucket to force remove non-empty bucket. ([#2495](https://github.com/neuro-inc/platform-client-python/issues/2495))
- Support `neuro -q ls` and `neuro -q blob ls` for quiet output enforcing. ([#2506](https://github.com/neuro-inc/platform-client-python/issues/2506))


Deprecations and Removals
-------------------------

- Replace `--http` option with `--http-port`, keep `--http` option as a hidden deprecated alternative, scheduled for removal later. ([#2501](https://github.com/neuro-inc/platform-client-python/issues/2501))
- Remove deprecated `neuro project init` command. ([#2502](https://github.com/neuro-inc/platform-client-python/issues/2502))
- Remove `client.job.tags()` method from SDK and `neuro job tags` command from CLI. ([#2503](https://github.com/neuro-inc/platform-client-python/issues/2503))
- Drop deprecated API from SDK ([#2505](https://github.com/neuro-inc/platform-client-python/issues/2505))


Neuro SDK/CLI 21.12.2 (2021-12-23)
==================================

Features
--------

- Sort CLI commands, groups and topics alphabetically. ([#2488](https://github.com/neuro-inc/platform-client-python/issues/2488))
- Add support for Open-Sourced user-less services deployment. ([#2492](https://github.com/neuro-inc/platform-client-python/issues/2492))


Bugfixes
--------

- Replace "Spend credits" with "Credits spent" in formatter. ([#2435](https://github.com/neuro-inc/platform-client-python/issues/2435))


Neuro SDK/CLI 21.12.1 (2021-12-22)
==================================

Bugfixes
--------

- Fix importing of asynccontextmanager from wrong place


Neuro SDK/CLI 21.12.0 (2021-12-21)
==================================

Features
--------

- Merge `config show-quota` into `config show` CLI command. ([#2436](https://github.com/neuro-inc/platform-client-python/issues/2436))
- Added admin commands to manager orgs and org-clusters:

  Managing orgs:

  - `neuro admin get-orgs`               Print the list of available orgs user has access to.
  - `neuro admin add-org <org_name>`     Create a new org.
  - `neuro admin remove-org <org_name>`  Drop a org. Removes all memberships, very dangerous operation.

  Managing org members:

  - `neuro admin get-org-users <org_name>`               List all members of orgs.
  - `neuro admin add-org-user <org_name> <username>`     Add user to the org.
  - `neuro admin remove-org-user <org_name> <username>`  Remove user from the org.

  Managing access of orgs to clusters:

  - `neuro admin get-org-clusters <cluster_name>`                     Print the list of all orgs in the cluster
  - `neuro admin add-org-cluster <cluster_name> <org_name>`           Add org access to specified cluster
  - `neuro admin get-org-cluster-quota  <cluster_name> <org_name>`    Get info about org quota in given cluster
  - `neuro admin set-org-cluster-quota [options] <cluster_name> <org_name>`    Set org cluster quota to given values
  - `neuro admin set-org-cluster-credits [options] <cluster_name> <org_name>`  Set org cluster credits to given value
  - `neuro admin add-org-cluster-credits [options] <cluster_name> <org_name>`  Add given values to org cluster balance

  Manging access of org members to clusters:

  - `neuro admin get-cluster-users --org <org_name> <cluster_name>`                      List all members of orgs added to cluster
  - `neuro admin add-cluster-user --org <org_name>  <cluster_name> <username>`           Add org member to cluster
  - `neuro admin remove-cluster-user --org <org_name> <cluster_name> <username>`         Remove org member user from the cluster.
  - `neuro admin get-user-quota --org <org_name>  <cluster_name> <username>`             Get info about org member quota in given cluster
  - `neuro admin set-user-quota [options] --org <org_name> <cluster_name> <username>`    Set org member quota in cluster to given values
  - `neuro admin set-user-credits [options] --org <org_name> <cluster_name> <username>`  Set org member credits in cluster to given value
  - `neuro admin add-user-credits [options] --org <org_name> <cluster_name> <username>`  Add given values to org member balance in cluster ([#2449](https://github.com/neuro-inc/platform-client-python/issues/2449))
- Option `-j`/`--jobs` in `neuro admin set-user-quota` is now required. Pass `unlimited` for setting no limit. Negative values are now rejected. ([#2453](https://github.com/neuro-inc/platform-client-python/issues/2453))
- Option `-c`/`--credits` in `neuro admin set-user-credits` and `neuro admin add-user-credits` is now required. Pass "unlimited" in `neuro admin set-user-credits` for setting no limit. Values "infinity", "nan" etc are now rejected. ([#2454](https://github.com/neuro-inc/platform-client-python/issues/2454))
- Added support of organizations.

  Current organization is displayed in `neuro config show`. It can be changed using `neuro config switch-org`. To least
  organizations you have access to in each cluster, use `neuro config get-clusters`.

  Also you can run job on behalf of organization. By default, `neuro run` will use current organization, but you
  can override it using `neuro run --org <some_org>`. ([#2465](https://github.com/neuro-inc/platform-client-python/issues/2465))


Bugfixes
--------

- Fix command description for `neuro admin show-cluster-options`. ([#2434](https://github.com/neuro-inc/platform-client-python/issues/2434))


Neuro SDK/CLI 21.11.4 (2021-11-25)
==================================

Bugfixes
--------

- Fix `neuro rm storage:...` command

Neuro SDK/CLI 21.11.3 (2021-11-25)
==================================

Features
--------

- Add Python 3.10 support. ([#2421](https://github.com/neuro-inc/platform-client-python/issues/2421))


Deprecations and Removals
-------------------------

- Drop Python 3.6 support. ([#2421](https://github.com/neuro-inc/platform-client-python/issues/2421))


Neuro SDK/CLI 21.11.2 (2021-11-23)
==================================

Features
--------

- Configure version checker settings by plugins. ([#2405](https://github.com/neuro-inc/platform-client-python/issues/2405))
- CLI startup time is 2 times shorter now. ([#2417](https://github.com/neuro-inc/platform-client-python/issues/2417))


Deprecations and Removals
-------------------------

- Deprecate `neuro project init` command, use `cookiecutter gh:neuro-inc/cookiecutter-neuro-project` instead. ([#2418](https://github.com/neuro-inc/platform-client-python/issues/2418))


Neuro SDK/CLI 21.11.1 (2021-11-17)
==================================

Features
--------

- Add support of symlinks in `neuro ls`. ([#2400](https://github.com/neuro-inc/platform-client-python/issues/2400))


Bugfixes
--------

- Fix sharing buckets using `neuro acl grant`. ([#2414](https://github.com/neuro-inc/platform-client-python/issues/2414))


Neuro SDK/CLI 21.11.0 (2021-11-08)
==================================

Features
--------

- Report job price in `neuro job status`, add support of organisation names in jobs. ([#2404](https://github.com/neuro-inc/platform-client-python/issues/2404))
- Raise dedicated `NotSupportedError` for unsupported REST API calls ([#2407](https://github.com/neuro-inc/platform-client-python/issues/2407))


Neuro SDK/CLI 21.10.0 (2021-10-25)
==================================

Features
--------

- Added support of open stack as bucket provider. ([#2371](https://github.com/neuro-inc/platform-client-python/issues/2371))
- Added `blob du <bucket_id_or_name>` command to change bucket's storage usage. ([#2372](https://github.com/neuro-inc/platform-client-python/issues/2372))
- Added support of bucket name in uris for bucket that do not belong to current user. ([#2385](https://github.com/neuro-inc/platform-client-python/issues/2385))
- Added first name, lastname, registered columns to `neuro admin get-cluster-users` output. ([#2387](https://github.com/neuro-inc/platform-client-python/issues/2387))
- Added "Spent credits" to add "neuro admin get-cluster-users". Splitted 'quota' into 'balance' and 'quota':

  - `neuro admin set-user-quota` changes only `max_running_jobs` quota.
  - `neuro admin set-user-credits` changes only `credits` balance of user.
  - `neuro admin add-user-credits` updates `credits` balance of user by delta. ([#2391](https://github.com/neuro-inc/platform-client-python/issues/2391))


Bugfixes
--------

- Fix fetching zero-size blob from S3 compatible bucket providers. ([#2394](https://github.com/neuro-inc/platform-client-python/issues/2394))


Neuro SDK/CLI 21.9.3 (2021-09-24)
===================================

Features
--------

- Added support of blob storage for azure clusters. ([#2284](https://github.com/neuro-inc/platform-client-python/issues/2284))
- Added support of blob storage for gcp clusters. ([#2293](https://github.com/neuro-inc/platform-client-python/issues/2293))
- Added `--read-only` flag to `neuro blob mkcredentials` to allow creation of read-only credentials. ([#2295](https://github.com/neuro-inc/platform-client-python/issues/2295))
- Added `neuro blob importbucket` command to import external bucket. External buckets support
  the same operations (`neuro blob ls/cp/rm/glob`), but it is impossible to generate persistent credentials
  for them using "neuro blob mkcredentials". ([#2297](https://github.com/neuro-inc/platform-client-python/issues/2297))
- Added `neuro blob sign-url <blob-uri>` command for generation of urls that grant temporal access to blob. ([#2299](https://github.com/neuro-inc/platform-client-python/issues/2299))
- Added command `neuro blob set-bucket-publicity <bucket> <"public"|"private">` to make bucket accessible for unauthorized
  users. ([#2306](https://github.com/neuro-inc/platform-client-python/issues/2306))
- Undeprecate `neuro job save` command, we decided to support this functionality in future. ([#2336](https://github.com/neuro-inc/platform-client-python/issues/2336))


Neuro SDK/CLI 21.9.2 (2021-09-02)
=================================

- Revert back ([#2274](https://github.com/neuro-inc/platform-client-python/issues/2274)); `pip install neuro-cli[awscli,boto3]` did not work well.


Neuro SDK/CLI 21.8.30 (2021-08-30)
==================================

Features
--------

- Implement URI autocompletion for "blob:" scheme. ([#2273](https://github.com/neuro-inc/platform-client-python/issues/2273))
- Provide `pip install neuro-cli[awscli,boto3]` extra dependencies for installing the compatible AWS CLI version.

  * `neuro-cli[awscli]` installs `awscli` package.

  * `neuro-cli[boto3]` installs `boto3` package.

  * `neuro-cli[awscli,boto3]` installs both. ([#2274](https://github.com/neuro-inc/platform-client-python/issues/2274))


Neuro SDK/CLI 21.8.27 (2021-08-27)
==================================

Features
--------

- Add support of minio provider as a bucket blob for onprem clusters ([#2271](https://github.com/neuro-inc/platform-client-python/issues/2271))


Bugfixes
--------

- Relax aiobotocore requirement; it allows working with the latest aiobotocore without publishing new Neuro SDK. ([#2270](https://github.com/neuro-inc/platform-client-python/issues/2270))


Neuro SDK/CLI 21.8.26 (2021-08-26)
==================================

Features
--------

- Add option `--since` in command `neuro logs`. Add parameter *since* in jobs.monitor(). ([#1964](https://github.com/neuro-inc/platform-client-python/issues/1964))
- Add option `--timestamps` in command `neuro logs`. Add parameter *timestamps* in jobs.monitor(). ([#2252](https://github.com/neuro-inc/platform-client-python/issues/2252))
- Implement public URI helpers. ([#2253](https://github.com/neuro-inc/platform-client-python/issues/2253))
- Reworked blob storage support:

  Bucket management commands:
  - use `neuro blob mkbucket` to create new bucket
  - use `neuro blob lsbucket` to list your buckets
  - use `neuro blob statbucket <bucket_id>` to retrieve info about single bucket
  - use `neuro blob rmbucket <bucket_id>` to delete bucket. Note that you can only delete empty buckets.

  Users can name buckets objects. The name should be unique between users buckets and can be used
  instead of bucket id.

  Bucket contents management commands:
  - use `neuro blob ls blob:<bucket_id>/<path_in_bucket>` to list bucket contents. Option `-r`
  disables file system emulation and displays all keys that start with <path_in_bucket>.
  - use `neuro blob glob blob:<bucket_id>/<glob_pattern>` to glob search objects in buckets.
  For example, `blob:my_bucket/**/*.txt` pattern will match all `.txt` files in `my_bucket`
  bucket.
  - use `neuro blob cp <src_uri> <dst_uri>` to copy data from/to bucket.
  - use `neuro blob rm blob:<bucket_id>/<path_in_bucket>` to delete elements from bucket. ([#2258](https://github.com/neuro-inc/platform-client-python/issues/2258))
- Implement URI autocompletion for bash shell. ([#2259](https://github.com/neuro-inc/platform-client-python/issues/2259))
- Added way to create persistent credentials to buckets to use in outside of the platform:

  - use `neuro blob mkcredentials <bucket1_id> <bucket2_id> ...` to create new credentials for specified buckets
  - use `neuro blob lscredentials` to list your buckets credentials
  - use `neuro blob statcredentials <credentials_id>` to retrieve info about single bucket credentials
  - use `neuro blob rmbucket <credentials_id>` to delete bucket credentials.

  Users can name buckets credentials. The name should be unique between users buckets credentials and can be used
  instead of bucket credentials id. ([#2264](https://github.com/neuro-inc/platform-client-python/issues/2264))


Deprecations and Removals
-------------------------

- Deprecate `neuro run IMAGE CMD`, use `neuro run IMAGE -- CMD` instead. The same for `neuro exec` command. ([#2260](https://github.com/neuro-inc/platform-client-python/issues/2260))
- Remove deprecated options older than 6 months. ([#2262](https://github.com/neuro-inc/platform-client-python/issues/2262))


Neuro SDK/CLI 21.8.12 (2021-08-12)
==================================

Features
--------

- Added possibility to disable PyPi version check via environment variable 'NEURO_CLI_DISABLE_PYPI_VERSION_CHECK'. ([#2237](https://github.com/neuro-inc/platform-client-python/issues/2237))
- Add parameter *separator* in jobs.monitor(). ([#2239](https://github.com/neuro-inc/platform-client-python/issues/2239))

- Support URI autocompletion in storage commands for ZSH shell. ([#2248](https://github.com/neuro-inc/platform-client-python/issues/2248))

Deprecations and Removals
-------------------------

- `neuro save` command is deprecated and will be removed in future CLI release. ([#2249](https://github.com/neuro-inc/platform-client-python/issues/2249))


Neuro SDK/CLI 21.7.29 (2021-07-29)
==================================

Bugfixes
--------

- Fix config permission bits for --pass-config mode ([#2233](https://github.com/neuro-inc/platform-client-python/issues/2233))

Deprecations and Removals
-------------------------

- Drop legacy code that puts configuration files for pass-config on storage. ([#2233](https://github.com/neuro-inc/platform-client-python/issues/2233))


Neuro SDK/CLI 21.7.28 (2021-07-28)
==================================

Features
--------

- Support VCD cluster config in generate-cluster-config command. ([#2193](https://github.com/neuro-inc/platform-client-python/issues/2193))
- Enabled writing of full logs for each CLI run to a file. Logs are generated under `~/.neuro/logs` folder and
  automatically removed after 3 days. ([#2211](https://github.com/neuro-inc/platform-client-python/issues/2211))
- Added `--cluster` option to `neuro run` command and `neuro disk`, `neuro secret` command groups. This option
  allows to perform actions for a specific cluster instead of current one. ([#2225](https://github.com/neuro-inc/platform-client-python/issues/2225))


Bugfixes
--------

- `_Admin.set_user_quota` method is fixed for cases, when the amount of credits equals to zero. ([#2229](https://github.com/neuro-inc/platform-client-python/issues/2229))
- Recover cursor after an abnormal exit (Ctrl-C). ([#2231](https://github.com/neuro-inc/platform-client-python/issues/2231))


Neuro SDK/CLI 21.7.9 (2021-07-09)
=================================

Features
--------

- All asynchronous iterators returned by API support now an asynchronous manager protocol. It is strongly preferable to use "asyn with" before iterating them. For example::

			async with client.jobs.list() as jobs:
				async for job in jobs:
					print(job.id) ([#2192](https://github.com/neuro-inc/platform-client-python/issues/2192))
- Added `neuro storage df` command that allows to retrieve cluster's storage disk usage. ([#2201](https://github.com/neuro-inc/platform-client-python/issues/2201))


Bugfixes
--------

- Removed additional '\n' from output of commands that print tokens. ([#2200](https://github.com/neuro-inc/platform-client-python/issues/2200))


Neuro SDK/CLI 21.6.23 (2021-06-23)
==================================

Features
--------


- Introduce NDJSONError exception, raise it instead of bare Exception in case of error in ndjson stream. ([#2187](https://github.com/neuro-inc/platform-client-python/issues/2187))


Bugfixes
--------


- Preserve volumes order in `client.parse.volumes(...)` call. ([#2183](https://github.com/neuro-inc/platform-client-python/issues/2183))


Neuro SDK/CLI 21.6.17 (2021-06-17)
==================================

Bugfixes
--------


- Expose `neuro_sdk.EnvParseResult` and `neuro_sdk.VolumeParseResult` names. ([#2177](https://github.com/neuro-inc/platform-client-python/issues/2177))


Neuro SDK/CLI 21.6.16 (2021-06-16)
==================================

Features
--------


- Dropped `role` argument from `neuro service-account create`: platform automatically generates
  new role for service account without any permissions. ([#2167](https://github.com/neuro-inc/platform-client-python/issues/2167))


Neuro SDK/CLI 21.6.9 (2021-06-09)
=================================

Bugfixes
--------

- Add missing requirement to `packaging`. ([#2160](https://github.com/neuro-inc/platform-client-python/issues/2160))


Neuro SDK/CLI 21.6.3 (2021-06-03)
==================================

Features
--------


- Add support of `--owner` and `--name` options to `neuro image ls`. ([#2104](https://github.com/neuro-inc/platform-client-python/issues/2104))

- Add option `--cluster` in commands `neuro ps`, `neuro top` and `neuro images`. ([#2125](https://github.com/neuro-inc/platform-client-python/issues/2125))

- Removed support of old runtime quota:
  - `neuro config show-quota` shows credits and max parallel jobs
  - `neuro admin add-user-quota/set-user-quota` only support credits and max parallel jobs
  - Added new command `neuro admin get-user-quota` to print user quota
  - `neuro admin get-cluster-user` now prints table with quota info for each user ([#2140](https://github.com/neuro-inc/platform-client-python/issues/2140))

- Added `neuro service-account` command group. The service account allow to create auth token that can be used
  for integration with third-party services.

  - `neuro service-account create --name optional-name ROLE` creates new service account
  - `neuro service-account ls` lists service accounts
  - `neuro service-account get ID_OR_NAME` retrives single service account
  - `nuero service-account rm ID_OR_NAME` removes service account and revokes token. ([#2147](https://github.com/neuro-inc/platform-client-python/issues/2147))


Neuro SDK/CLI 21.5.14 (2021-05-14)
==================================

Features
--------


- Ignore files in parent directories are now used when upload a directory to storage or blob storage. ([#1901](https://github.com/neuro-inc/platform-client-python/issues/1901))

- Add spinners to the some commands that take time to execute. ([#2105](https://github.com/neuro-inc/platform-client-python/issues/2105))

- All job related commands support now jobs on other clusters. Commands `neuro exec`, `neuro port-forward`, `neuro logs` and `neuro job save` only support jobs on other clusters if they are specified by URI (jobs on the current cluster can be also specified by bare ID or name). ([#2116](https://github.com/neuro-inc/platform-client-python/issues/2116))


Bugfixes
--------


- Provide forward compatibility with click 8.0 ([#2126](https://github.com/neuro-inc/platform-client-python/issues/2126))

- Fix hints for 'neuro run' command. ([#2127](https://github.com/neuro-inc/platform-client-python/issues/2127))

- Fix compatibility with click==8.0. ([#2126](https://github.com/neuro-inc/platform-client-python/issues/2126))


Neuro SDK/CLI 21.4.17 (2021-04-17)
==================================

Features
--------


- Commands `neuro ps` and `neuro top` support now outputting several fields in one table cell. By default fields ID and NAME and fields STATUS and WHEN are merged. This saves horisontal space and improves output of long fields (e.g. COMMAND, DESCRIPTION or TAGS). ([#2062](https://github.com/neuro-inc/platform-client-python/issues/2062))

- Added automatic re-attach if container is still alive after `neuro run`/`neuro attach` disconnects. ([#2085](https://github.com/neuro-inc/platform-client-python/issues/2085))

- Added warning about actual privilege level if `neuro grant` grants privilege less then user already has. ([#2092](https://github.com/neuro-inc/platform-client-python/issues/2092))


Bugfixes
--------


- Fixed unexpected behavior in `neuro admin update-resource-preset` when working with existing preset:
  Now there are two commands:
  - `neuro admin add-resource-preset` to add new preset, options use default values if not specified
  - `neuro admin update-resource-preset` to update existing preset, options use previous values if not specified
  Also dropped `cluster_name` argument to fix bug when presets were overwritten by active cluster presets. ([#2091](https://github.com/neuro-inc/platform-client-python/issues/2091))


Neuro SDK/CLI 21.4.13 (2021-04-13)
==================================

Features
--------


- Added option `--share` in `neuro job run`. It allows to share a created job with specified user or role. ([#2079](https://github.com/neuro-inc/platform-client-python/issues/2079))


Bugfixes
--------


- Fixed handling jobs with `--pass-config` in `neuro job generate-run-command`. ([#2074](https://github.com/neuro-inc/platform-client-python/issues/2074))


Neuro SDK/CLI 21.4.2 (2021-04-02)
=================================

Bugfixes
--------


- Bump pinned rich version to >=10.0.1 ([#2072](https://github.com/neuro-inc/platform-client-python/issues/2072))


Neuro SDK/CLI 21.4.1 (2021-04-01)
=================================

Features
--------


- Allow bumping jobs life span using `neuro jobs bump-life-span <timedelta>`. ([#2020](https://github.com/neuro-inc/platform-client-python/issues/2020))

- Make a job status reason always printed by neuro status if it is available. ([#2047](https://github.com/neuro-inc/platform-client-python/issues/2047))

- Add support of automatic re-login after config errors. This allows to upgrade
  to a new CLI version without manual re-login. ([#2048](https://github.com/neuro-inc/platform-client-python/issues/2048))

- Made more precise datetime formatting for neuro status: now hours and minutes are always printed. Seconds are printed
  for event that happened in the last hour. ([#2053](https://github.com/neuro-inc/platform-client-python/issues/2053))

- Storage operations support now URIs with cluster names different from the current cluster name. You can now list or copy to/from other cluster's storage without switching the current cluster name. ([#2054](https://github.com/neuro-inc/platform-client-python/issues/2054))

- Added printing of ids of removed disk in `neuro disk rm`. ([#2056](https://github.com/neuro-inc/platform-client-python/issues/2056))

- Allow to specify date and time in --since/--until relatively to current moment. For example,
  `neuro ps --since 1d` will show jobs that were created during last day. ([#2059](https://github.com/neuro-inc/platform-client-python/issues/2059))

- Image operations support now URIs with cluster names different from the current cluster name. ([#2066](https://github.com/neuro-inc/platform-client-python/issues/2066))

- Added hint about headless login when `neuro login` executes in non-GUI environment. ([#2068](https://github.com/neuro-inc/platform-client-python/issues/2068))


Bugfixes
--------


- Do not add implicit '\n's to `neuro job generate_run_command <job-id>` command output. ([#2034](https://github.com/neuro-inc/platform-client-python/issues/2034))

- Fix bad formatting in `neuro run` command. ([#2055](https://github.com/neuro-inc/platform-client-python/issues/2055))

- Do not kill a non-tty job when running in non-tty mode automatically.
  This allows to exit from `neuro run ... | tee` using `^C` without killing a job. ([#2063](https://github.com/neuro-inc/platform-client-python/issues/2063))


Neuro SDK/CLI 21.3.3 (2021-03-03)
=================================

Features
--------


- Added option `--format` in `neuro top` for specifying the output columns. It is similar to option `--format` of `neuro ps`, but support several additional columns. ([#2000](https://github.com/neuro-inc/platform-client-python/issues/2000))

- Added filtering options in `neuro top`: `--owner`, `--name`, `--tag`, `--description`, `--since` and `--until`. They are similar to corresponding options in `neuro ps`. By default shown only jobs of the current user, specify `--owner=ALL` to show jobs of all users. ([#2001](https://github.com/neuro-inc/platform-client-python/issues/2001))

- Add option `--sort` in `neuro top`. ([#2002](https://github.com/neuro-inc/platform-client-python/issues/2002))

- Drop cluster_name and description from default output of `neuro ps` command. ([#2009](https://github.com/neuro-inc/platform-client-python/issues/2009))

- Allow deletion images without tag. Support multiple arguments for `neuro image rm` command. ([#2010](https://github.com/neuro-inc/platform-client-python/issues/2010))


Bugfixes
--------


- Support job statuses "suspended" and "unknown" in `neuro ps` and `neuro top`. ([#2011](https://github.com/neuro-inc/platform-client-python/issues/2011))


Neuro SDK/CLI 21.2.19 (2021-02-19)
==================================

Bugfixes
--------


- Fixed parsing of huge job payloads. ([#2004](https://github.com/neuro-inc/platform-client-python/issues/2004))


Neuro SDK/CLI 21.2.16 (2021-02-16)
==================================

Features
--------


- Added support of named disks:
  - create new disk by `neuro disk create --name <disk-name> STORAGE` command
  - name can be used to get/delete disk: `neuro disk get <disk-name>` or `neuro disk delete <disk-name>`
  - name can be used to mount disk: `neuro run -v disk:<disk-name>:/mnt/disk ...` ([#1983](https://github.com/neuro-inc/platform-client-python/issues/1983))

- Added printing of job id when `neuro flow` or `neuro attach` exits. ([#1993](https://github.com/neuro-inc/platform-client-python/issues/1993))

- Added "Life span ends" field to `neuro status <job-id>`. ([#1994](https://github.com/neuro-inc/platform-client-python/issues/1994))

- Now all datetime fields are printed in "humanized form". Use `neuro --iso-datetime-format <command> ...` to
  force ISO 8601 format. ([#1995](https://github.com/neuro-inc/platform-client-python/issues/1995))

- Added recovering of attachment to job after internet connection issue in `neuro attach` and `neuro run`. ([#1996](https://github.com/neuro-inc/platform-client-python/issues/1996))


Neuro SDK/CLI 21.2.11 (2021-02-11)
==================================

Features
--------


- `neuro top` supports now multiple jobs. If multiple jobs is specified at command line, it outputs a table for that jobs. If no jobs are specified, it outputs all active user's job. ([#418](https://github.com/neuro-inc/platform-client-python/issues/418))

- Added private option `--x-trace-all` which forces distribute tracing. ([#1973](https://github.com/neuro-inc/platform-client-python/issues/1973))

- Add `neuro job generate-run-command <job-id-or-name>` to simplify reruning of jobs. ([#1977](https://github.com/neuro-inc/platform-client-python/issues/1977))

- Added new options to `neuro ps`:
  `--distinct`: Show only first job if names are same.
  `--recent-first/--recent-last`: Show newer jobs first or last ([#1981](https://github.com/neuro-inc/platform-client-python/issues/1981))


Deprecations and Removals
-------------------------


- Soft-deprecate `neuro job tags` command. ([#1840](https://github.com/neuro-inc/platform-client-python/issues/1840))


Neuro SDK/CLI 21.1.13 (2021-01-13)
==================================

Features
--------


- Removed support of deprecated `--status=all` in `neuro ps`. Use `--all` instead. ([#1883](https://github.com/neuro-inc/platform-client-python/issues/1883))

- Refresh config after resource presets are updated. ([#1899](https://github.com/neuro-inc/platform-client-python/issues/1899))


Bugfixes
--------


- Don't open browser on `login-with-token`. ([#1748](https://github.com/neuro-inc/platform-client-python/issues/1748))

- Suppress non-critical neuro configuration database errors. ([#1816](https://github.com/neuro-inc/platform-client-python/issues/1816))

- Fixed unintentional interpretation of sequences like `:+1` and `[b]` in descriptions, commands, paths, URIs, etc when output on the console. ([#1917](https://github.com/neuro-inc/platform-client-python/issues/1917))


Neuro SDK/CLI 20.12.16 (2020-12-16)
===================================

Bugfixes
--------


- Fix unstable imports of `rich` tool. ([#1911](https://github.com/neuro-inc/platform-client-python/issues/1911))


Neuro SDK/CLI 20.12.14 (2020-12-14)
===================================

Features
--------


- Extract `neuromation.api` into `neuro-sdk` package, rename `neuromation` to `neuro-cli`. ([#1892](https://github.com/neuro-inc/platform-client-python/issues/1892))


Bugfixes
--------


- Generating the URI string for `RemoteImage` now correctly escapes special characters like "#", "%", "?" in image name and tag. ([#1895](https://github.com/neuro-inc/platform-client-python/issues/1895))

- Fixed conflict between logging and showing progress in `neuro cp -vv`. Use the `rich` library for outputting colored logs. ([#1897](https://github.com/neuro-inc/platform-client-python/issues/1897))


Neuromation 20.12.7 (2020-12-07)
================================

Features
--------


- Added --privileged flag to `neuro run`. Added corresponding argument `privileged` to `jobs.start`. ([#1879](https://github.com/neuro-inc/platform-client-python/issues/1879))

- Added Disk life-span information to the `neuro disk ls --long-format` and `neuro disk get` commands. ([#1880](https://github.com/neuro-inc/platform-client-python/issues/1880))


Bugfixes
--------


- Added support of filtering by statuses "cancelled" and "suspended" in `neuro ps`. ([#1881](https://github.com/neuro-inc/platform-client-python/issues/1881))


Neuromation 20.12.2 (2020-12-02)
================================

Features
--------


- Add `-l` option to `neuro image tags` for long output format ([#1855](https://github.com/neuro-inc/platform-client-python/issues/1855))

- Add `-f` flag to `neuro image rm` to force delete images that have multiple tag references ([#1828](https://github.com/neuro-inc/platform-client-python/issues/1828))

- Enable display of non-zero restarts count for all jobs (previously only jobs with proper --restart-policy had this field). ([#1859](https://github.com/neuro-inc/platform-client-python/issues/1859))

- Added cluster resource presets management commands.
  Added `Preemptible Node` column in resource presets format in `neuro config show`. ([#1863](https://github.com/neuro-inc/platform-client-python/issues/1863))

- Pass preset instead of container resources to job api. ([#1864](https://github.com/neuro-inc/platform-client-python/issues/1864))

- `neuro blob cp` uses now partial read when retry to download a blob. ([#1865](https://github.com/neuro-inc/platform-client-python/issues/1865))

- Change jobs capacity API endpoint. ([#1872](https://github.com/neuro-inc/platform-client-python/issues/1872))

- Add disk column to `admin get-clusters` command. ([#1873](https://github.com/neuro-inc/platform-client-python/issues/1873))

- Added options `--update` and `--continue` for command `neuro blob cp`. Added optional boolean parameters `update` and `continue_` to the corresponding API. ([#1875](https://github.com/neuro-inc/platform-client-python/issues/1875))


Bugfixes
--------


- Fixed parsing file modification time in Blob Storage. ([#1874](https://github.com/neuro-inc/platform-client-python/issues/1874))


Neuromation 20.11.18 (2020-11-18)
=================================

Features
--------


- Moved pass_config option to API. Now it uses config completely encoded into ENV variable. ([#1814](https://github.com/neuro-inc/platform-api-clients/issues/1814))

- Added support of max running jobs quota. The `neuro admin set-user-quota -j <count>` command configures
  this quota for user. By default, a new job cannot be created after the quota is reached, but the `--wait-for-seat`
  flag allows creating a job that will wait for another job to stop. ([#1827](https://github.com/neuro-inc/platform-api-clients/issues/1827))

- When the connection is lost during transferring files `neuro cp` retries now only sending and retrieving new data instead of starting file operation from the start. Added optional parameters *offset* and *size* in method `storage.open()` for partial reading. Added method `storage.write()` for overwriting the part of the file. ([#1831](https://github.com/neuro-inc/platform-api-clients/issues/1831))

- Added option `--continue` for command `neuro cp`.
  It specified, copy only the part of the source file
  past the end of the destination file and append it
  to the destination file if the destination file is
  newer and not longer than the source file.
  Otherwise copy the whole file.
  Added corresponding keyword-only boolean parameter `continue_` to the API. ([#1841](https://github.com/neuro-inc/platform-api-clients/issues/1841))

- Add support of `SUSPENDED` job status. ([#1844](https://github.com/neuro-inc/platform-api-clients/issues/1844))

- Added support of `neuro ps --owner ME`. This allows to filter current users jobs. ([#1845](https://github.com/neuro-inc/platform-api-clients/issues/1845))

- The active cluster name can now be specified in local configuration file. ([#1846](https://github.com/neuro-inc/platform-api-clients/issues/1846))


Neuromation 20.11.10 (2020-11-10)
=================================

Features
--------


- Add `neuro image rm` command for removing images from remote registries ([#1770](https://github.com/neuro-inc/platform-api-clients/issues/1770))

- Allowed to share disks. ([#1811](https://github.com/neuro-inc/platform-api-clients/issues/1811))

- Added support of multiple disk removal: `neuro disk rm disk-id-1 disk-id-2` works properly now. ([#1821](https://github.com/neuro-inc/platform-api-clients/issues/1821))

- Added displaying of restarts count for restartable jobs. Added `restarts` field to `JobStatusHistory`. ([#1822](https://github.com/neuro-inc/platform-api-clients/issues/1822))


Neuromation 20.10.30 (2020-10-30)
=================================

Features
--------


- Bump ``aiohttp`` to >= 3.7.2 in the library requirements, drop transient dependencies ``multidict`` and ``yarl``. Support Python 3.8 and Python 3.9 ([#1802](https://github.com/neuro-inc/platform-api-clients/issues/1802))


Neuromation 20.10.22 (2020-10-22)
=================================

Features
--------


- Allowed to share secrets. ([#1791](https://github.com/neuro-inc/platform-api-clients/issues/1791))


Neuromation 20.10.7 (2020-10-07)
================================

Features
--------


- Made `neuro completion patch` idempotent. ([#1760](https://github.com/neuromation/platform-api-clients/issues/1760))


Bugfixes
--------


- Suppress connection errors when cluster is not available in `neuro config show`. ([#1763](https://github.com/neuromation/platform-api-clients/issues/1763))


Neuromation 20.9.24 (2020-09-24)
================================

Features
--------


- Fragment, query, user, password and port parts are not allowed now in URIs (these parts were silently ignored before).
  Fixed support of local file paths containing characters like "#", "%", ":", "?", "@" and "~". ([#1531](https://github.com/neuromation/platform-api-clients/issues/1531))

- Implemented disks management commands. ([#1716](https://github.com/neuromation/platform-api-clients/issues/1716))

- `neuro run` allows now to specify disk volumes using `-v disk:<DISK>:<PATH>:<RW_FLAG>`. ([#1721](https://github.com/neuromation/platform-api-clients/issues/1721))

- Added support of `created_at` and `last_usage` field of disks. Added `--long-format` option to `neuro disk ls`. ([#1729](https://github.com/neuromation/platform-api-clients/issues/1729))

- Memory amount parsing now supports of both `b` and `B` suffixes for specifying decimal
  quantities. Improved `neuro disk create` docs. ([#1731](https://github.com/neuromation/platform-api-clients/issues/1731))

- Added a `--life-span` argument to `neuro disk create`. Added a `life_span` argument in `client.disks.create()`. ([#1734](https://github.com/neuromation/platform-api-clients/issues/1734))

- Added output to `neuro disk rm` and `neuro secret rm` when `-v/--verbose` global flag is set. ([#1738](https://github.com/neuromation/platform-api-clients/issues/1738))

- Quite mode command `neuro -q disk ls` now prints simple list of disk ids. ([#1740](https://github.com/neuromation/platform-api-clients/issues/1740))

- Command `neuro image tags` outputs now a list of tags instead of a list of images. ([#1741](https://github.com/neuromation/platform-api-clients/issues/1741))

- Added support of `--full-uri` to `neuro disk get`. ([#1747](https://github.com/neuromation/platform-api-clients/issues/1747))

- Show a deprecation warning for `--life-span=0` in `neuro run` command. ([#1749](https://github.com/neuromation/platform-api-clients/issues/1749))

- Change the color scheme for job statuses. The yellow color is for the cancellation, cyan is for pending jobs. ([#1752](https://github.com/neuromation/platform-api-clients/issues/1752))


Neuromation 20.9.3 (2020-09-03)
===============================

Bugfixes
--------


- Commands `neuro image ls` and `neuro image tags` and corresponding API `images.ls()` and `images.tags()` can now return more than 100 items. ([#1606](https://github.com/neuromation/platform-api-clients/issues/1606))

- Make `neuromation.api.SecretFile` class public ([#1714](https://github.com/neuromation/platform-api-clients/issues/1714))


Neuromation 20.9.2 (2020-09-02)
===============================

Features
--------


- Added support of `CANCELED` state. ([#1696](https://github.com/neuromation/platform-api-clients/issues/1696))

- Added support of error messages in streamed delete response. ([#1697](https://github.com/neuromation/platform-api-clients/issues/1697))

- Colorize `neuro ps` output. ([#1698](https://github.com/neuromation/platform-api-clients/issues/1698))

- Added way to destroy browser session by during `neuro logout`. ([#1699](https://github.com/neuromation/platform-api-clients/issues/1699))

- Remove `--volume=ALL` option from CLI and move volume and env variable parsing from CLI module to the `Parser` class in API ([#1707](https://github.com/neuromation/platform-api-clients/issues/1707))

- Command `neuro acl list` accepts now a URI prefix for filtering. API functions `users.get_acl()` and `users.get_shares()` accept now the *uri* argument. ([#1708](https://github.com/neuromation/platform-api-clients/issues/1708))

- `neuro run` supports now multiple `--env-file` options. ([#1710](https://github.com/neuromation/platform-api-clients/issues/1710))


Neuromation 20.8.19 (2020-08-19)
================================

Features
--------


- Show add available jobs counts (cluster capacity) in `neuro config show` command. ([#1687](https://github.com/neuromation/platform-api-clients/issues/1687))

- Make JobStatus calculation forward-compatible; `JobStatus.UNKNOWN` is returned for
  unknown statuses but the code doesn't raise `ValueError` at least. ([#1688](https://github.com/neuromation/platform-api-clients/issues/1688))


Neuromation 20.8.14 (2020-08-14)
================================

- Pin `yarl` version dependency to 1.5.1+.


Neuromation 20.8.13 (2020-08-13)
================================

Features
--------


- Implement `FileStatus.uri` property. ([#1648](https://github.com/neuromation/platform-api-clients/issues/1648))

- Add support of plugin-defined config parameters ([#1657](https://github.com/neuromation/platform-api-clients/issues/1657))

- Added `find_project_root` function ([#1660](https://github.com/neuromation/platform-api-clients/issues/1660))

- Added `neuro rm --progress` and `progress` argument to `Storage.rm` for tracking delete progress ([#1664](https://github.com/neuromation/platform-api-clients/issues/1664))

- Added `internal_hostname_named` to `JobDescription` and to output of `neuro job status`. ([#1675](https://github.com/neuromation/platform-api-clients/issues/1675))

- Added logging of `X-Error` error description in `neuro port-forward`. ([#1676](https://github.com/neuromation/platform-api-clients/issues/1676))

- Added printing of documentation link to `nuero login` command ([#1680](https://github.com/neuromation/platform-api-clients/issues/1680))

- Added `neuro admin show-cluster-options` command for displaying possible cluster configuration options. ([#1681](https://github.com/neuromation/platform-api-clients/issues/1681))


Neuromation 20.7.28 (2020-07-28)
================================

Features
--------


- `neuro ps` supports now columns "created", "started" and "finished" (hidden by default). ([#1020](https://github.com/neuromation/platform-api-clients/issues/1020))

- `neuro status` shows now the job's http port. ([#1375](https://github.com/neuromation/platform-api-clients/issues/1375))

- Long list of tags for `neuro status` is now wrapped. ([#1408](https://github.com/neuromation/platform-api-clients/issues/1408))

- `neuro ps` supports now the "life_span" column (hidden by default). ([#1448](https://github.com/neuromation/platform-api-clients/issues/1448))

- Command aliases are now supported if not logged in. ([#1480](https://github.com/neuromation/platform-api-clients/issues/1480))

- Added support of the `--schedule-timeout` option in `neuro run`. ([#1499](https://github.com/neuromation/platform-api-clients/issues/1499))

- Added commands for adding and removing roles: `neuro acl add-role` and `neuro acl remove-role`. ([#1582](https://github.com/neuromation/platform-api-clients/issues/1582))

- Support expansion of the user home directory ("~") in the file path argument in `neuro secret add`. ([#1610](https://github.com/neuromation/platform-api-clients/issues/1610))

- Put `--help` option first in the help output for a command or command group ([#1627](https://github.com/neuromation/platform-api-clients/issues/1627))

- Officially support Python 3.8. ([#1638](https://github.com/neuromation/platform-api-clients/issues/1638))

- Create a topic about secrets management and usage. ([#1640](https://github.com/neuromation/platform-api-clients/issues/1640))


Bugfixes
--------


- Fixed "division by zero" error when copy from `/dev/stdin` to storage. ([#1129](https://github.com/neuromation/platform-api-clients/issues/1129))

- Fixed support of local images whose name starts with Neuro registry prefix, e.g. `registry.neu.ro/alice/imagename`. ([#1159](https://github.com/neuromation/platform-api-clients/issues/1159))

- Fixed support of relative image URIs with numeric name, like `image:5000`. ([#1631](https://github.com/neuromation/platform-api-clients/issues/1631))

- When resolve job URI with other user's name and job name (like `job:/bob/test-name`), the owner name no longer ignored when the shared job is not found. ([#1633](https://github.com/neuromation/platform-api-clients/issues/1633))


Deprecations and Removals
-------------------------


- Removed support of `--volume=HOME` in `neuro run`. ([#1202](https://github.com/neuromation/platform-api-clients/issues/1202))


Neuromation 20.7.14 (2020-07-14)
================================

Features
--------


- Implement secrets management commands. ([#1545](https://github.com/neuromation/platform-api-clients/issues/1545))

- `neuro run` allows now to specify secrets: either as a file `-v secret:<KEY>:<PATH>` or as an environment variable `-e <NAME>=secret:<KEY>`. ([#1558](https://github.com/neuromation/platform-api-clients/issues/1558))

- Support azure cluster config file generation. ([#1577](https://github.com/neuromation/platform-api-clients/issues/1577))

- Implement `--port-forward` option for `run` and `attach` commands. ([#1601](https://github.com/neuromation/platform-api-clients/issues/1601))

- Take Secrets Service URL from `/config`. ([#1607](https://github.com/neuromation/platform-api-clients/issues/1607))


Deprecations and Removals
-------------------------


- Deprecate and hide `submit` command. ([#1602](https://github.com/neuromation/platform-api-clients/issues/1602))


Neuromation 20.7.9 (2020-07-09)
===============================

Bugfixes
--------


- Always set "LESS=-R" env variable to fix outputs with scrolling, e.g. "neuro help" ([#1595](https://github.com/neuromation/platform-api-clients/issues/1595))

- Fix a warning raised by `neuro job port-forward` command on Python 3.6 ([#1592](https://github.com/neuromation/platform-api-clients/issues/1592))


Neuromation 20.7.3 (2020-07-03)
===============================

Bugfixes
--------


- Increase timeout for waiting for jobs exit after finishing attached session from 15
  seconds to 15 minutes. ([#1584](https://github.com/neuromation/platform-api-clients/issues/1584))


Neuromation 20.6.23 (2020-06-23)
================================

Features
--------


- A `.neuroignore` file specifies files that `neuro cp` should ignore when upload directories to the storage or object storage. Syntax and semantic are similar to `.gitignore` files. ([#1446](https://github.com/neuromation/platform-api-clients/issues/1446))

- API: `Client.jobs.run()` supports now relative storage URIs for volumes. ([#1464](https://github.com/neuromation/platform-api-clients/issues/1464))

- Explicit options `--exclude` and `--include` no longer disable the defaults from the storage.cp-exclude configuration variable. Use explicit `--exclude="*" or --include="*"` to override default patterns. ([#1489](https://github.com/neuromation/platform-api-clients/issues/1489))

- Support leading and trailing slashes (`/`) in filters. Leading slash prevents matching in subdirectories, e.g. `/*.txt` matches `spam.txt`, but not `dir/spam.txt`, while `*.txt` matches both of them. Patterns with trailing slash match only directories, while patterns without trailing slash match both directories and files. ([#1490](https://github.com/neuromation/platform-api-clients/issues/1490))

- Implement attach/exec/interactive-run using WebSockets. ([#1497](https://github.com/neuromation/platform-api-clients/issues/1497))

- Implement port forwarding over WebSockets. ([#1555](https://github.com/neuromation/platform-api-clients/issues/1555))

- Added the `--exclude-from-files` option in `neuro cp`.

  API: Added the optional parameter `ignore_file_names` in the `upload_dir()` methods of `storage` and `blob_storage`. ([#1560](https://github.com/neuromation/platform-api-clients/issues/1560))


Bugfixes
--------


- Fix swallowing underscores in `neuro status`. ([#1565](https://github.com/neuromation/platform-api-clients/issues/1565))


Deprecations and Removals
-------------------------


- Drop deprected and hidden `neuro storage load` command. ([#1542](https://github.com/neuromation/platform-api-clients/issues/1542))


Neuromation 20.6.10 (2020-06-10)
================================

Bugfixes
--------


- Suppress annoying message about improperly handled GeneratorExit exception. ([#1525](https://github.com/neuromation/platform-api-clients/issues/1525))


Neuromation 20.6.2 (2020-06-02)
===============================

Features
--------

- API: `Storage.ls()` is an asynchronous generator now. ([#1457](https://github.com/neuromation/platform-api-clients/issues/1457))

- Added the `--restart` option to `neuro run` and `neuro submit` and API. ([#1459](https://github.com/neuromation/platform-api-clients/issues/1459))

- API: `Jobs.list()` is an asynchronous generator now. ([#1473](https://github.com/neuromation/platform-api-clients/issues/1473))

- `neuro ps` now outputs local date instead of UTC and interprets `--since` and `--until` options as local time if the timezone is not specified. ([#1477](https://github.com/neuromation/platform-api-clients/issues/1477))

- autocomplete job name/id ([#1485](https://github.com/neuromation/platform-api-clients/issues/1485))

- Unencodable characters are now replaced with `?` or `U+FFFE` when output to the stdout. ([#1502](https://github.com/neuromation/platform-api-clients/issues/1502))


Bugfixes
--------


- Fixed downloading a file when it is restarted for some reasons.  The newly downloaded data no longer appended to a previously downloaded data, but overwrites it. ([#1521](https://github.com/neuromation/platform-api-clients/issues/1521))

- Fixed parsing image URIs with the single slash after scheme, like `image:/otheruser/imagename`. ([#1505](https://github.com/neuromation/platform-api-clients/issues/1505))


Neuromation 20.4.15 (2020-04-15)
================================

Features
--------


- Added `--since` and `--until` options to `neuro ps`. ([#1461](https://github.com/neuromation/platform-api-clients/issues/1461))


Bugfixes
--------


- Make exit code of `job run` command more reliable. ([#1470](https://github.com/neuromation/platform-api-clients/issues/1470))


Neuromation 20.4.6 (2020-04-06)
===============================

Features
--------


- Commands `neuro ps`, `neuro job status`, `nauro image list` and `neuro acl list` output now URIs in the short form if possible. Use the new `--full-uri` option to get full qualified URIs. ([#1330](https://github.com/neuromation/platform-api-clients/issues/1330))

- Changed interpretatation of cluster related URIs (with schemes `storage:`, `image:` and `job:`) with missed host and path started with `/`. `storage:/user/path` is expanded now to `storage://{defaultcluster}/user/path`, so you do not need to specify the cluster name when refer to other user's resources on the same cluster. ([#1424](https://github.com/neuromation/platform-api-clients/issues/1424))

- Implement `neuro storage tree` command for displaying the directory tree on storage. ([#1435](https://github.com/neuromation/platform-api-clients/issues/1435))

- Filter patterns are now more compatible with `.gitignore`. Added support of `**` which matches zero or more path components. `?` and `*` no longer match `/`. Patterns which does not contain `/` at the beginning or middle matches now files in subdirectories. ([#1444](https://github.com/neuromation/platform-api-clients/issues/1444))


Neuromation 20.3.23 (2020-03-23)
================================

Bugfixes
--------


- Bump `typing_extensions` dependency version to satisfy CLI requirements. ([#1421](https://github.com/neuromation/platform-api-clients/issues/1421))


Neuromation 20.3.20 (2020-03-20)
================================

Bugfixes
--------


- Fix `--pass-config` error: File exists: '/root/.neuro'. ([#1415](https://github.com/neuromation/platform-api-clients/issues/1415))


Neuromation 20.3.18 (2020-03-18)
================================

Features
--------


- Support job run-time limit: `neuro run --life-span "1d2h3m"`. ([#1325](https://github.com/neuromation/platform-api-clients/issues/1325))

- For cluster-specific resources (with schemes `storage`, `image` and `job`) client now use URIs containing the cluster name, e.g. `storage://{clustername}/{username}/{path}` instead of `storage://{username}/{path}`. Relative URI `storage:{path}` will be expanded to absolute URI containing the current cluster name and the user name: `storage://{clustername}/{username}/{path}`. Same for `image` and `job` schemes. ([#1341](https://github.com/neuromation/platform-api-clients/issues/1341))

- Added 'neuro image ls -l' option, which also prints Docker URL-s ([#1354](https://github.com/neuromation/platform-api-clients/issues/1354))

- Added the `-u` option in `neuro acl list` to specify a role or user to which resources are available and for which they are shared. ([#1355](https://github.com/neuromation/platform-api-clients/issues/1355))

- Sort `neuro admin get-cluster-users` by name. ([#1359](https://github.com/neuromation/platform-api-clients/issues/1359))

- Steal config files on `neuro job --pass-config`. ([#1361](https://github.com/neuromation/platform-api-clients/issues/1361))

- Support hidden files on the storage. Hide names started with a dot by default, provide ``neuro ls --all`` option to show all files. ([#1362](https://github.com/neuromation/platform-api-clients/issues/1362))

- Add HTTP tracing of neuro login commands. ([#1387](https://github.com/neuromation/platform-api-clients/issues/1387))

- Support job tags: `neuro run --tag=experiment-1`, `neuro ps --tag=experiment-1`. ([#1393](https://github.com/neuromation/platform-api-clients/issues/1393))

- Support job tags listing: `neuro job tags`. ([#1396](https://github.com/neuromation/platform-api-clients/issues/1396))

- Optionally display job's tags in `neuro ps` (the feature needs to be explicitly enabled in `.neuro.toml` config file). ([#1406](https://github.com/neuromation/platform-api-clients/issues/1406))


Bugfixes
--------


- Fix the alias finding routine when user is not logged in. ([#1360](https://github.com/neuromation/platform-api-clients/issues/1360))

- `neuro kill` exits now non-zero code if it failed to kill any job in the list. ([#1272](https://github.com/neuromation/platform-api-clients/issues/1272))

- Support un-quoted commands for neuro-exec: `neuro exec bash -c "ls && pwd"` is now a valid syntax. ([#1321](https://github.com/neuromation/platform-api-clients/issues/1321))


Neuromation 20.2.24 (2020-02-24)
=================================

Features
--------


- Support custom columns format for ``neuro ps`` command. ([#1288](https://github.com/neuromation/platform-api-clients/issues/1288))

- Support custom aliases. ([#1320](https://github.com/neuromation/platform-api-clients/issues/1320))

- Removed support of `~` in URIs (like `storage://~/path/to`). Relative URIs can be used instead (like `storage:path/to`). Support of tilde in local file paths (like `~/path/to`) has been preserved. ([#1329](https://github.com/neuromation/platform-api-clients/issues/1329))


Neuromation 20.01.22 (2020-01-22)
=================================

Features
--------


- `--env-file` now allows blank lines and comments (lines starting with "#") in the file. ([#1208](https://github.com/neuromation/platform-api-clients/issues/1208))

- Send the usage statistics to Google Analytics ([#1286](https://github.com/neuromation/platform-api-clients/issues/1286))

- Use Sqlite for saving the ``~/.neuro/db`` configuration file. ([#1298](https://github.com/neuromation/platform-api-clients/issues/1298))


Bugfixes
--------


- Fix columns width and aligning for ``neurp ps --format=<>`` command. ([#1302](https://github.com/neuromation/platform-api-clients/issues/1302))

- Fix ps-format documentation issues. ([#1303](https://github.com/neuromation/platform-api-clients/issues/1303))

- Parameters specified in ps-format now always override default values. `width` takes priority over `min` and `max`, `max` takes priority over `min`. ([#1310](https://github.com/neuromation/platform-api-clients/issues/1310))


Neuromation 20.01.15 (2020-01-15)
=================================

Features
--------


- Add `neuro admin add-user-quota` and `neuro admin set-user-quota` commands to control user quotas ([#1142](https://github.com/neuromation/platform-api-clients/issues/1142))

- Added options `--exclude` and `--include` in `neuro storage cp`. ([#1182](https://github.com/neuromation/platform-api-clients/issues/1182))

- Adjust NAME column of `neuro ps` so that grep by name works. ([#1189](https://github.com/neuromation/platform-api-clients/issues/1189))

- Read ``neuro ps --format`` spec from config files if present. ([#1294](https://github.com/neuromation/platform-api-clients/issues/1294))

- Read ``neuro cp`` filters from user configuration file. ([#1295](https://github.com/neuromation/platform-api-clients/issues/1295))


Neuromation 19.12.19 (2019-12-19)
=================================

Features
--------


- Now `neuro images` do not require the installed Docker. ([#1071](https://github.com/neuromation/platform-api-clients/issues/1071))

- Implement `neuro config get-clusters` command. ([#1177](https://github.com/neuromation/platform-api-clients/issues/1177))

- Convert configuration file into configuration directory, now it is `~/.neuro` folder. ([#1183](https://github.com/neuromation/platform-api-clients/issues/1183))

- Implement `neuro config switch-cluster` for switching between available clusters. ([#1217](https://github.com/neuromation/platform-api-clients/issues/1217))

- Implement `neuro admin get-clusters` command. ([#1223](https://github.com/neuromation/platform-api-clients/issues/1223))

- Implement `neuro admin add-cluster` command. ([#1224](https://github.com/neuromation/platform-api-clients/issues/1224))

- Add ``neuro admin generate-cluster-config`` command. ([#1227](https://github.com/neuromation/platform-api-clients/issues/1227))

- `neuro project init` now supports argument to set default value for generated project directory ([#1230](https://github.com/neuromation/platform-api-clients/issues/1230))


Bugfixes
--------


- Correctly process both quoted command arguments (`neuro run python:latest "python3 -c 'import os'") as well as unquoted version (`neuro run python:latest python3 -c 'import os'`). ([#1229](https://github.com/neuromation/platform-api-clients/issues/1229))


Neuromation 19.11.20 (2019-11-20)
=================================

Features
--------


- Trace sent HTTP requests and received replies to stderr if `--trace` flag is passed. ([#467](https://github.com/neuromation/platform-api-clients/issues/467))

- Display `Cluster` field for job status and listing commands. ([#874](https://github.com/neuromation/platform-api-clients/issues/874))

- Display `Entrypoint` field for job status command. ([#924](https://github.com/neuromation/platform-api-clients/issues/924))

- Display volumes information for `neuro status` command. ([#1003](https://github.com/neuromation/platform-api-clients/issues/1003))

- Option `--volume=HOME` deprecated. ([#1009](https://github.com/neuromation/platform-api-clients/issues/1009))

- Provide client.presets property, update docs. ([#1078](https://github.com/neuromation/platform-api-clients/issues/1078))

- Retry storage operations in case of some errors. ([#1107](https://github.com/neuromation/platform-api-clients/issues/1107))

- `neuro kill` will continue work if multiple jobs specified but you haven't required permissions for some of them. ([#1122](https://github.com/neuromation/platform-api-clients/issues/1122))

- Introduce `neuro config show-quota`. ([#1141](https://github.com/neuromation/platform-api-clients/issues/1141))

- Use pager for long lists. ([#1152](https://github.com/neuromation/platform-api-clients/issues/1152))

- Add global option '--hide-token/--no-hide-token' to be used together with '--trace' for preventing the user's token from being printed to stderr for safety reasons. ([#1158](https://github.com/neuromation/platform-api-clients/issues/1158))

- Suppress security checks for config files if NEUROMATION_TRUSTED_CONFIG_PATH environment variable is on. ([#1173](https://github.com/neuromation/platform-api-clients/issues/1173))


Bugfixes
--------


- When running a job with `--detach` option `neuro` now returns an error status if job fails to start at all (e.g., when cluster scale up fails). If job starts successfully (regardless of its run result) `neuro run` with `--detach` returns 0 like before. ([#1059](https://github.com/neuromation/platform-api-clients/issues/1059))

- Provide default arguments for api.Resources constructor to keep broken backward compatibility. ([#1070](https://github.com/neuromation/platform-api-clients/issues/1070))

- Fix help message for `neuro project init`: in fact, the command does not accept an argument. ([#1080](https://github.com/neuromation/platform-api-clients/issues/1080))

- Process 502 Bad Gateway as a separate exception, don't miss it with 400 Bad Request. ([#1111](https://github.com/neuromation/platform-api-clients/issues/1111))

- Wait for `ThreadPoolExecutor` finish befor exit from the program. ([#1144](https://github.com/neuromation/platform-api-clients/issues/1144))


Neuromation 19.9.23 (2019-09-23)
================================

Features
--------


- Introduce `neuro project init` for scaffolding an empty project. ([#1043](https://github.com/neuromation/platform-api-clients/issues/1043))

- `neuro cp -r` now works with non-directories. ([#1053](https://github.com/neuromation/platform-api-clients/issues/1053))

- Disable logging of annoying SSL errors. ([#1065](https://github.com/neuromation/platform-api-clients/issues/1065))

- Make image commands work on Windows. ([#1067](https://github.com/neuromation/platform-api-clients/issues/1067))

- Fix bug with job-name resolution introduced in release 19.8.19: do not print annoying warning messages if more than one job with specified name was found. ([#1034](https://github.com/neuromation/platform-api-clients/issues/1034))

- Fix `neuro job save` timing out too early. ([#1062](https://github.com/neuromation/platform-api-clients/issues/1062))

Neuromation 19.9.10 (2019-09-10)
================================

Features
--------


- Improved displaying a progress of copying many files. ([#1034](https://github.com/neuromation/platform-api-clients/issues/1034))


Deprecations and Removals
-------------------------


- Deprecate `neuro storage load` command. ([#1028](https://github.com/neuromation/platform-api-clients/issues/1028))


Neuromation 19.9.2 (2019-09-02)
===============================

Features
--------


- Due to `certifi` update delays, show certifi package error not earlier than two weeks after the latest version was released. ([#944](https://github.com/neuromation/platform-api-clients/issues/944))

- Support streaming output for `neuro-save` command. ([#946](https://github.com/neuromation/platform-api-clients/issues/946))

- Implement mounting all available volumes: `neuro run --volume=ALL`. ([#974](https://github.com/neuromation/platform-api-clients/issues/974))

- Uploading/downloading of a directory containing many small files is now 4-10 times faster. ([#981](https://github.com/neuromation/platform-api-clients/issues/981))

- Support Cloud TPU: new cli options `--tpu-type`, `--tpu-sw-version` added. ([#982](https://github.com/neuromation/platform-api-clients/issues/982))

- Support job operations via job-URI (e.g., `neuro status job://owner-name/job-name`). ([#988](https://github.com/neuromation/platform-api-clients/issues/988))

- Support job filtering by owner: `neuro ps -o user-1 --owner=user-2`. ([#990](https://github.com/neuromation/platform-api-clients/issues/990))

- Added the `--update` option in `neuro storage cp`.  It makes the command copying the source file only when it is newer than the destination file or when the destination file is missing. ([#1007](https://github.com/neuromation/platform-api-clients/issues/1007))

- Added the `-d` (`--directory`) option in `neuro storage ls` which makes the command to list directories themselves, not their contents. ([#1012](https://github.com/neuromation/platform-api-clients/issues/1012))


Neuromation 19.8.23 (2019-08-23)
================================

Features
--------


- `FileStatus.permission` now is `Action`, was `str`. ([#963](https://github.com/neuromation/platform-api-clients/issues/963))


Bugfixes
--------


- Fix regression: restore port-forward functionality. ([#979](https://github.com/neuromation/platform-api-clients/issues/979))


Neuromation 19.8.19 (2019-08-19)
================================

Features
--------


- Change default interactivity option for `neuro exec`: by default, interactive `--tty` will be used. ([#942](https://github.com/neuromation/platform-api-clients/issues/942))

- Use `Optional[datetime]` in `JobStatusHistory` `.created_at`, `.started_at`, `.finished_at` instead of `str`. ([#955](https://github.com/neuromation/platform-api-clients/issues/955))

- `neuro storage cp` is now up to 2 times faster for a directory with many small files. ([#958](https://github.com/neuromation/platform-api-clients/issues/958))

- Refactor port forwarding api to use async context manager for controlling a time of port
  forwarding process. ([#959](https://github.com/neuromation/platform-api-clients/issues/959))


Bugfixes
--------


- Support remote images with registry `host:port`. ([#939](https://github.com/neuromation/platform-api-clients/issues/939))


Neuromation 19.8.1 (2019-08-01)
===============================

Features
--------


- The `-p/--non-preemptible` parameter for `neuro run` has been removed in favor in embedding it into presets coming from the server. ([#928](https://github.com/neuromation/platform-api-clients/issues/928))

- Show progress for `neuro cp` by default. ([#933](https://github.com/neuromation/platform-api-clients/issues/933))

- Use dataclasses in image progress API ([#935](https://github.com/neuromation/platform-api-clients/issues/935))


Neuromation 19.7.26 (2019-07-26)
================================

Features
--------


- Add option `ps --all`, deprecate `ps -s all`. ([#538](https://github.com/neuromation/platform-api-clients/issues/538))

- Forbid mixing arguments and CLI options in `run`, `submit` and `exec` commands. Options (parameters starting from dash or double dash, e.g. `-n` and `--name`) should prepend arguments (e.g. `image:ubuntu:latest`). All tailed options belong to executed container command, not to neuro CLI itself. ([#927](https://github.com/neuromation/platform-api-clients/issues/927))


Neuromation 19.7.17 (2019-07-17)
================================

Features
--------


- The behavior of `neuro storage mv` is now closer to the behavior of the `mv` command.  It moves now files inside the target directory if it exists and moves a file under the new name otherwise.  Added also options `--target-directory` (`-t`) and `--no-target-directory` (`-T`). ([#203](https://github.com/neuromation/platform-api-clients/issues/203))

- `neuro job submit` and `neuro job run` command now support `--pass-config` option. This option ensures your local neuromation config file is uploaded to your job allowing you to executre `neuro` commands from the container. ([#827](https://github.com/neuromation/platform-api-clients/issues/827))

- Add `neuro image tags` command to list all tags for a given image ([#852](https://github.com/neuromation/platform-api-clients/issues/852))

- Stabilize jobs API ([#879](https://github.com/neuromation/platform-api-clients/issues/879))

- `neuro storage cp`, `neuro storage mv` and `neuro storage rm` support now globbing for source arguments.  Globbing can be disabled by specifying new option `--no-glob`.  Added command `neuro storage glob` which lists resources matching patterns. ([#889](https://github.com/neuromation/platform-api-clients/issues/889))


Neuromation 19.7.4 (2019-07-04)
===============================

Features
--------


- Implemented `neuro job browse`. Added the `--browse` flag to `neuro job submit` and `neuro job run`. ([#571](https://github.com/neuromation/platform-api-clients/issues/571))

- Added the global `--quiet` option, opposite to `--verbose`. Both options are additive. The `--quite` options for `neuro job` and `neuro image` are deprecated now. ([#848](https://github.com/neuromation/platform-api-clients/issues/848))

- Drop `neuromation.api.NetworkPortForwarding` for the sake of `neuromation.api.HTTPPort` ([#861](https://github.com/neuromation/platform-api-clients/issues/861))

- The output of "storage" commands in verbose mode is now more similar to the output of corresponding POSIX command. In particular ``neuro -v storage cp -r`` outputs a line for every copied file or directory. ([#869](https://github.com/neuromation/platform-api-clients/issues/869))

- The behavior of the `neuro storage cp` is now closer to the behavior of the `cp` command.  It now copies files inside the target directory if it exists and copies a file under the new name otherwise.  Added also options `--target-directory` (`-t`) and `--no-target-directory` (`-T`). ([#870](https://github.com/neuromation/platform-api-clients/issues/870))


Bugfixes
--------


- Fix certifi upgrade suggestion text. ([#845](https://github.com/neuromation/platform-api-clients/issues/845))


Neuromation 19.6.12 (2019-06-12)
================================

Features
--------


- Make non-preemtible mode default. ([#829](https://github.com/neuromation/platform-api-clients/issues/829))


Neuromation 19.6.10 (2019-06-10)
================================

Bugfixes
--------


- Improve storage operations stability by supporting sticky sessions. ([#832](https://github.com/neuromation/platform-api-clients/issues/832))


Neuromation 19.6.5 (2019-06-05)
===============================

Bugfixes
--------


- Relax pyyaml version requirement to don't force users to upgrade it if pyyaml was installed by anaconda or another non-pip installer. ([#828](https://github.com/neuromation/platform-api-clients/issues/828))


Neuromation 19.6.4 (2019-06-04)
===============================

Bugfixes
--------


- Don't run version checks if config is not loaded by CLI command. ([#826](https://github.com/neuromation/platform-api-clients/issues/826))


Neuromation 19.6.3 (2019-06-03)
===============================

Features
--------


- Changes in `neuro store mkdir` behavior: fails if the directory already exists or parent directories do not exist. Add option `--parents` to make parent directories as needed and ignore existing directories. ([#131](https://github.com/neuromation/platform-api-clients/issues/131))

- Changes in `neuro store rm` behavior: removes only files by default, add option `--recursive` to remove directories. ([#354](https://github.com/neuromation/platform-api-clients/issues/354))

- Storage commands (`neuro storage ls`, `neuro storage cp`, `neuro storage mv`, `neuro storage rm`) accept now variable number of arguments. This allows to copy or remove several files by one command. ([#784](https://github.com/neuromation/platform-api-clients/issues/784))

- Implement `neuro config login-headless` command. ([#793](https://github.com/neuromation/platform-api-clients/issues/793))

- Changes in interpretation URIs with absolute path and without host name. `storage:///foo/bar` means now the same as `storage://foo/bar` instead of `storage://{currentuser}/foo/bar`, and `storage:///` can be used for access to the storage root directory. ([#808](https://github.com/neuromation/platform-api-clients/issues/808))

- `neuro storage cp` now supports copying to/from non-regular files like character devices and named pipes. In particular this allows to output the file to the stdout or get the input from the stdin (`/dev/stdout` and `/dev/stdin` on Linux, `CON` on Windows). ([#813](https://github.com/neuromation/platform-api-clients/issues/813))

- Relax certifi required version. Raise a warning if the package should be updated. ([#819](https://github.com/neuromation/platform-api-clients/issues/819))


Bugfixes
--------


- Allow to logout even if config file is broken. ([#792](https://github.com/neuromation/platform-api-clients/issues/792))


Neuromation 19.5.13 (2019-05-13)
================================

Features
--------


- Print exposed HTTP for named jobs ([#736](https://github.com/neuromation/platform-api-clients/issues/736))

- Support retrieving server config for authorized users. ([#766](https://github.com/neuromation/platform-api-clients/issues/766))


Neuromation 19.4.23 (2019-04-23)
================================

Features
--------


- Implement *job run* command. ([#652](https://github.com/neuromation/platform-api-clients/issues/652))


Bugfixes
--------


- Fix image name parser to substitute lastest tag automatically. ([#729](https://github.com/neuromation/platform-api-clients/issues/729))


Neuromation 19.4.16 (2019-04-16)
================================

Features
--------


- New option `--neuromation-config` for using alternative config file location. Environment variable `NEUROMATION_CONFIG` can be used as option.
  New command `neuro config docker` allows to use `docker image push/pull` commands with platform registry. ([#381](https://github.com/neuromation/platform-api-clients/issues/381))

- `neuro port-forward` command now accepts multiple local-remote port pairs in order to forward several ports by a single command. ([#632](https://github.com/neuromation/platform-api-clients/issues/632))

- Support job names. ([#648](https://github.com/neuromation/platform-api-clients/issues/648))

- Make progress argument for storage API optional. ([#687](https://github.com/neuromation/platform-api-clients/issues/687))

- Rename neuromation.client to neuromation.api ([#688](https://github.com/neuromation/platform-api-clients/issues/688))

- Implement `neuro config login-with-token TOKEN URL` command. ([#712](https://github.com/neuromation/platform-api-clients/issues/712))


Bugfixes
--------


- Don't allow to submit image names starting with dash. ([#526](https://github.com/neuromation/platform-api-clients/issues/526))

- Respect `--network-timeout` option in `logs` and `cp` operations. ([#703](https://github.com/neuromation/platform-api-clients/issues/703))


Deprecations and Removals
-------------------------


- Remove deprecated functionality: `neuro model`, `neuro config id_rsa` and `neuro job submit --ssh` option. ([#700](https://github.com/neuromation/platform-api-clients/issues/700))


Neuromation 0.7.2 (2019-03-25)
==============================

Features
--------


- Change the default API endpoint to `https://staging.neu.ro/api/v1` ([#666](https://github.com/neuromation/platform-api-clients/issues/666))


Neuromation 0.7.1 (2019-03-15)
==============================

Bugfixes
--------


- Fix incorrect `--volume` parsing under windows ([#635](https://github.com/neuromation/platform-api-clients/issues/635))


Neuromation 0.7.0 (2019-03-14)
==============================

Features
--------


- New flag `--http-auth/--no-http-auth` which controls authentication for forwarded HTTP port. Enabled by default. ([#604](https://github.com/neuromation/platform-api-clients/issues/604))


Neuromation 0.6.2 (2019-03-07)
==============================

Bugfixes
--------


- Increase wait time to finish on POSIX platforms. It dignificantly decreases a chance of error report after CLI command executions. ([#597](https://github.com/neuromation/platform-api-clients/issues/597))

- Fix forward compatibility with platform server. ([#599](https://github.com/neuromation/platform-api-clients/issues/599))


Neuromation 0.6.1 (2019-03-04)
==============================

Bugfixes
--------


- Close version checker properly in case of error in a command execution. ([#586](https://github.com/neuromation/platform-api-clients/issues/586))

- Pin aiohttp to 3.5+ to satisfy minimal supported CLI version. ([#587](https://github.com/neuromation/platform-api-clients/issues/587))


Neuromation 0.6.0 (2019-03-01)
==============================

Features
--------


- Extended '/dev/shm' space (`--extshm`) turned on by default ([#449](https://github.com/neuromation/platform-api-clients/issues/449))

- Add support for server-side job list filtering (speedup of the `neuro ps`) ([#474](https://github.com/neuromation/platform-api-clients/issues/474))

- Several UX improvements. ([#486](https://github.com/neuromation/platform-api-clients/issues/486))

- `neuro store ls` now supports colored output, _LS_COLORS_(GNU) or _LSCOLORS_(BSD) environment variable required. ([#487](https://github.com/neuromation/platform-api-clients/issues/487))

- Improve shell completion logic, make shell type argument mandatory. ([#506](https://github.com/neuromation/platform-api-clients/issues/506))

- Add Http URL to neuro job submit output ([#527](https://github.com/neuromation/platform-api-clients/issues/527))

- Added neuro port-forward command to forward a port of a job exposed during job submit to a local one. ([#535](https://github.com/neuromation/platform-api-clients/issues/535))

- Support Windows platform ([#548](https://github.com/neuromation/platform-api-clients/issues/548))


Bugfixes
--------


- Fix parsing image URIs. ([#539](https://github.com/neuromation/platform-api-clients/issues/539))

- Don't fetch PyPI if `--disable-pypi-version-check` is on. ([#559](https://github.com/neuromation/platform-api-clients/issues/559))


Neuromation 0.4.0 (2019-02-12)
==============================

Features
--------


- Check the lastest PyPI neuromation release, suggest to upgrade if PyPI has a newer version. ([#308](https://github.com/neuromation/platform-api-clients/issues/308))

- Changes in `neuro store ls` behavior: display files by columns by default, add option `-l` for long output, display one per line for pipes by default. ([#427](https://github.com/neuromation/platform-api-clients/issues/427))

- Set up the platform to work with the new platform DNS names. ([#495](https://github.com/neuromation/platform-api-clients/issues/495))


Bugfixes
--------


- Use colored mode only if all stdin, stdout, and stderr are tty. ([#473](https://github.com/neuromation/platform-api-clients/issues/473))

- Improved login error reporting ([#477](https://github.com/neuromation/platform-api-clients/issues/477))


Neuromation 0.3.0 (2019-02-01)
==============================

Features
--------


- Add `-p/-P` shortcuts for `--preemtible/--non-preemtible` for `neuro submit` command. ([#458](https://github.com/neuromation/platform-api-clients/issues/458))

- Wait for job start/failure on job submit. ([#356](https://github.com/neuromation/platform-api-clients/issues/356))

- Support `-v` as a shortcut for `--volume` in `neuro submit ...` command. ([#383](https://github.com/neuromation/platform-api-clients/issues/383))

- Improve resource URI normalization and print normalized URIs back to the user. ([#457](https://github.com/neuromation/platform-api-clients/issues/457))

- Re-organize CLI commands for better UI/UX experience. Obsolete commands are hidden but still supported. ([#460](https://github.com/neuromation/platform-api-clients/issues/460))


Neuromation 0.2.2 (2019-01-31)
==============================

Features
--------


- Add top-level aliases for the most frequent commands. ([#439](https://github.com/neuromation/platform-api-clients/issues/439))

- Better formatting for examples section. ([#446](https://github.com/neuromation/platform-api-clients/issues/446))


Bugfixes
--------


- Bump `click` version to `7.0+`. ([#437](https://github.com/neuromation/platform-api-clients/issues/437))

- Temporary disable scary logging about unhandled exception. ([#438](https://github.com/neuromation/platform-api-clients/issues/438))

- Fix an error in local path normalization. ([#443](https://github.com/neuromation/platform-api-clients/issues/443))


Neuromation 0.2.1 (2019-01-29)
==============================

Features
--------


- Implement ``neuro job top`` ([#412](https://github.com/neuromation/platform-api-clients/issues/412))

- Pretty format output for ``neuro config show`` command, print current authentication token by ``neuro config show-token``. ([#426](https://github.com/neuromation/platform-api-clients/issues/426))

- Check `~/.nmrc` config file for strict `0o600` permissions. ([#430](https://github.com/neuromation/platform-api-clients/issues/430))


Deprecations and Removals
-------------------------


- Drop `--token` and `--url` parameters from the root command, use `neuro login` and `neuro config url` to setup config parameters. ([#430](https://github.com/neuromation/platform-api-clients/issues/430))


Neuromation 0.2.0 (2019-01-28)
==============================

Features
--------


- Deep refactor ``neuro store`` command and corresponding API client. ([#324](https://github.com/neuromation/platform-api-clients/issues/324))

- Default API URL switched to HTTPS for _neuro_ cli ([#325](https://github.com/neuromation/platform-api-clients/issues/325))

- Job resource output formatting for command `neuro job status` changed ([#328](https://github.com/neuromation/platform-api-clients/issues/328))

- `neuro image pull/push` command improved for support different names/tags for images, introduced 'image://' scheme for image referencing. ([#349](https://github.com/neuromation/platform-api-clients/issues/349))

- Implement --show-traceback command line option to show python traceback in case of top-level error ([#365](https://github.com/neuromation/platform-api-clients/issues/365))

- Added new option `--insecure` for storing auth in plain text file instead system keyring. ([#366](https://github.com/neuromation/platform-api-clients/issues/366))

- New `neuro image ls` command for listing custom images available on platform repository. ([#367](https://github.com/neuromation/platform-api-clients/issues/367))

- Added new command `neuro job exec` to execute commands in already running job without ssh server. ([#373](https://github.com/neuromation/platform-api-clients/issues/373))

- Display Preemptible in job status output ([#393](https://github.com/neuromation/platform-api-clients/issues/393))

- Make the client work on Python 3.7 ([#402](https://github.com/neuromation/platform-api-clients/issues/402))

- Implement ``neuro job top`` ([#412](https://github.com/neuromation/platform-api-clients/issues/412))


Deprecations and Removals
-------------------------


- Jobs datastructure refactored ([#320](https://github.com/neuromation/platform-api-clients/issues/320))

- Removed _keyrings.cryptfile_ from project dependencies. Please remove it self if upgrade _neuromation_. ([#366](https://github.com/neuromation/platform-api-clients/issues/366))


Misc
----

- [#285](https://github.com/neuromation/platform-api-clients/issues/285), [#393](https://github.com/neuromation/platform-api-clients/issues/393)
