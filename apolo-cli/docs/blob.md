# blob

Blob storage operations

## Usage

```bash
apolo blob [OPTIONS] COMMAND [ARGS]...
```

Blob storage operations.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_cp_](blob.md#cp) | Copy blobs into and from Blob Storage |
| [_du_](blob.md#du) | Get storage usage for BUCKET |
| [_glob_](blob.md#glob) | List resources that match PATTERNS |
| [_importbucket_](blob.md#importbucket) | Import an existing bucket |
| [_ls_](blob.md#ls) | List buckets or bucket contents |
| [_lsbucket_](blob.md#lsbucket) | List buckets |
| [_lscredentials_](blob.md#lscredentials) | List bucket credentials |
| [_mkbucket_](blob.md#mkbucket) | Create a new bucket |
| [_mkcredentials_](blob.md#mkcredentials) | Create a new bucket credential |
| [_rm_](blob.md#rm) | Remove blobs from bucket |
| [_rmbucket_](blob.md#rmbucket) | Remove bucket BUCKET |
| [_rmcredentials_](blob.md#rmcredentials) | Remove bucket credential BUCKET\_CREDENTIAL |
| [_set-bucket-publicity_](blob.md#set-bucket-publicity) | Change public access settings for BUCKET |
| [_sign-url_](blob.md#sign-url) | Make signed url for blob in bucket |
| [_statbucket_](blob.md#statbucket) | Get bucket BUCKET |
| [_statcredentials_](blob.md#statcredentials) | Get bucket credential BUCKET\_CREDENTIAL |


### cp

Copy blobs into and from Blob Storage


#### Usage

```bash
apolo blob cp [OPTIONS] [SOURCES]... [DESTINATION]
```

Copy blobs into and from Blob Storage.

Either `SOURCES` or `DESTINATION`
should have `blob://` scheme.
If scheme is omitted, file:// scheme is assumed.
It is currently not possible to
copy files between Blob Storage (`blob://`)
destination, nor with `storage://`
scheme paths.

Use `/dev/stdin` and
`/dev/stdout` file names to upload a file from standard input
or output to
stdout.

Any number of --exclude and --include options can be passed.  The
filters that appear later in the command take precedence over filters
that
appear earlier in the command.  If neither --exclude nor
--include options are
specified the default can be changed using the
storage.cp-exclude
configuration variable documented in
"apolo help user-config".

File
permissions, modification times and other attributes will not be passed to
Blob Storage metadata during upload.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--continue_ | Continue copying partially-copied files. Only for copying from Blob Storage. |
| _--exclude-from-files FILES_ | A list of file names that contain patterns for exclusion files and directories. Used only for uploading. The default can be changed using the storage.cp-exclude-from-files configuration variable documented in "apolo help user-config" |
| _--exclude TEXT_ | Exclude files and directories that match the specified pattern. |
| _--include TEXT_ | Don't exclude files and directories that match the specified pattern. |
| _--glob / --no-glob_ | Expand glob patterns in SOURCES with explicit scheme.  _\[default: glob\]_ |
| _-T, --no-target-directory_ | Treat DESTINATION as a normal file. |
| _-p, --progress / -P, --no-progress_ | Show progress, on by default. |
| _-r, --recursive_ | Recursive copy, off by default |
| _-t, --target-directory DIRECTORY_ | Copy all SOURCES into DIRECTORY. |
| _-u, --update_ | Copy only when the SOURCE file is newer than the destination file or when the destination file is missing. |



### du

Get storage usage for BUCKET


#### Usage

```bash
apolo blob du [OPTIONS] BUCKET
```

Get storage usage for `BUCKET`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### glob

List resources that match PATTERNS


#### Usage

```bash
apolo blob glob [OPTIONS] [PATTERNS]...
```

List resources that match `PATTERNS`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--full-uri_ | Output full bucket URI. |



### importbucket

Import an existing bucket


#### Usage

```bash
apolo blob importbucket [OPTIONS]
```

Import an existing bucket.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--aws-access-key-id AWS\_ACCESS\_KEY\_ID_ | AWS access\_key\_id to use to access the bucket.  Required when PROVIDER is 'aws' |
| _--aws-endpoint-url AWS\_ENDPOINT_ | AWS endpoint to use to access the bucket. Usually you need to set this if you use non-AWS S3 compatible provider |
| _--aws-region-name AWS\_REGION_ | AWS region to use to access the bucket. |
| _--aws-secret-access-key AWS\_SECRET\_ACCESS\_KEY_ | AWS secret\_access\_key to use to access the bucket. Required when PROVIDER is 'aws' |
| _--azure-storage-account-url AZURE\_STORAGE\_ACCOUNT\_URL_ | Azure account url. Usually it has following format: https://&lt;account\_id&gt;.blob.core.windows.net Required when PROVIDER is 'azure' |
| _--azure-storage-credential AZURE\_STORAGE\_CREDENTIAL_ | Azure storage credential that grants access to imported bucket. Either this or AZURE\_SAS is required when PROVIDER is 'azure' |
| _--azure-storage-sas-token AZURE\_SAS_ | Azure shared access signature token that grants access to imported bucket. Either this or AZURE\_STORAGE\_CREDENTIAL is required when PROVIDER is 'azure' |
| _--cluster CLUSTER_ | Perform in a specified cluster \(the current cluster by default\). |
| _--gcp-sa-credential GCP\_SA\_CREDNETIAL_ | GCP service account credential in form of base64 encoded json string that grants access to imported bucket. Required when PROVIDER is 'gcp' |
| _--name NAME_ | Optional bucket name |
| _--org ORG_ | Perform in a specified org \(the current org by default\). |
| _--project PROJECT_ | Perform in a specified project \(the current project by default\). |
| _--provider PROVIDER_ | Bucket provider that hosts bucket  _\[required\]_ |
| _--provider-bucket-name EXTERNAL\_NAME_ | Name of bucket \(or container in case of Azure\) inside the provider  _\[required\]_ |



### ls

List buckets or bucket contents


#### Usage

```bash
apolo blob ls [OPTIONS] [PATHS]...
```

List buckets or bucket contents.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-l_ | use a long listing format. |
| _--full-uri_ | Output full bucket URI. |
| _-h, --human-readable_ | with -l print human readable sizes \(e.g., 2K, 540M\). |
| _-r, --recursive_ | List all keys under the URL path provided, not just 1 level depths. |



### lsbucket

List buckets


#### Usage

```bash
apolo blob lsbucket [OPTIONS]
```

List buckets.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--all-orgs_ | Show buckets in all orgs. |
| _--all-projects_ | Show buckets in all projects. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--full-uri_ | Output full bucket URI. |
| _--long-format_ | Output all info about bucket. |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### lscredentials

List bucket credentials


#### Usage

```bash
apolo blob lscredentials [OPTIONS]
```

List bucket credentials.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |



### mkbucket

Create a new bucket


#### Usage

```bash
apolo blob mkbucket [OPTIONS]
```

Create a new bucket.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Perform in a specified cluster \(the current cluster by default\). |
| _--name NAME_ | Optional bucket name |
| _--org ORG_ | Perform in a specified org \(the current org by default\). |
| _--project PROJECT_ | Perform in a specified project \(the current project by default\). |



### mkcredentials

Create a new bucket credential


#### Usage

```bash
apolo blob mkcredentials [OPTIONS] BUCKETS...
```

Create a new bucket credential.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Perform in a specified cluster \(the current cluster by default\). |
| _--name NAME_ | Optional bucket credential name |
| _--org ORG_ | Perform in a specified org \(the current org by default\). |
| _--project PROJECT_ | Perform in a specified project \(the current project by default\). |
| _--read-only_ | Make read-only credential |



### rm

Remove blobs from bucket


#### Usage

```bash
apolo blob rm [OPTIONS] PATHS...
```

Remove blobs from bucket.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--glob / --no-glob_ | Expand glob patterns in PATHS  _\[default: glob\]_ |
| _-p, --progress / -P, --no-progress_ | Show progress, on by default in TTY mode, off otherwise. |
| _-r, --recursive_ | remove directories and their contents recursively |



### rmbucket

Remove bucket BUCKET


#### Usage

```bash
apolo blob rmbucket [OPTIONS] BUCKETS...
```

Remove bucket `BUCKET`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Perform on a specified cluster \(the current cluster by default\). |
| _-f, --force_ | Force removal of all blobs inside bucket |
| _--org ORG_ | Perform on a specified org \(the current org by default\). |
| _--project PROJECT_ | Perform on a specified project \(the current project by default\). |



### rmcredentials

Remove bucket credential BUCKET_CREDENTIAL


#### Usage

```bash
apolo blob rmcredentials [OPTIONS] CREDENTIALS...
```

Remove bucket credential `BUCKET_CREDENTIAL`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Perform on a specified cluster \(the current cluster by default\). |



### set-bucket-publicity

Change public access settings for BUCKET


#### Usage

```bash
apolo blob set-bucket-publicity [OPTIONS] BUCKET {public|private}
```

Change public access settings for `BUCKET`

#### Examples

```bash

$ apolo blob set-bucket-publicity my-bucket public
$ apolo blob set-bucket-publicity my-bucket private
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Perform on a specified cluster \(the current cluster by default\). |
| _--org ORG_ | Perform on a specified org \(the current org by default\). |
| _--project PROJECT_ | Perform on a specified project \(the current project by default\). |



### sign-url

Make signed url for blob in bucket


#### Usage

```bash
apolo blob sign-url [OPTIONS] PATH
```

Make signed url for blob in bucket.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--expires TIMEDELTA_ | Duration this signature will be valid in the format '1h2m3s'  _\[default: 1h\]_ |



### statbucket

Get bucket BUCKET


#### Usage

```bash
apolo blob statbucket [OPTIONS] BUCKET
```

Get bucket `BUCKET`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |
| _--full-uri_ | Output full bucket URI. |
| _--org ORG_ | Look on a specified org \(the current org by default\). |
| _--project PROJECT_ | Look on a specified project \(the current project by default\). |



### statcredentials

Get bucket credential BUCKET_CREDENTIAL


#### Usage

```bash
apolo blob statcredentials [OPTIONS] BUCKET_CREDENTIAL
```

Get bucket credential `BUCKET_CREDENTIAL`.

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--cluster CLUSTER_ | Look on a specified cluster \(the current cluster by default\). |


