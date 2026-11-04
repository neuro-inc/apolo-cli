# image

Container image operations

## Usage

```bash
apolo image [OPTIONS] COMMAND [ARGS]...
```

Container image operations.

**Commands:**
| Usage | Description |
| :--- | :--- |
| [_digest_](image.md#digest) | Get digest of an image from remote registry |
| [_inspect_](image.md#inspect) | Show platforms and attestations of an image |
| [_ls_](image.md#ls) | List images |
| [_pull_](image.md#pull) | Pull an image from platform registry |
| [_push_](image.md#push) | Push an image to platform registry |
| [_rm_](image.md#rm) | Remove image from platform registry |
| [_size_](image.md#size) | Get image size |
| [_tags_](image.md#tags) | List tags for image in platform registry |


### digest

Get digest of an image from remote registry


#### Usage

```bash
apolo image digest [OPTIONS] IMAGE
```

Get digest of an image from remote registry

Image name must be `URL` with
image:// scheme.
Image name must contain tag.

#### Examples

```bash

$ apolo image digest image:/other-project/alpine:shared
$ apolo image digest image:myimage:latest
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### inspect

Show platforms and attestations of an image


#### Usage

```bash
apolo image inspect [OPTIONS] IMAGE
```

Show platforms and attestations of an image

Image name must be `URL` with
image:// scheme.
Image name must contain tag.

Lists the platform images of a
multi-platform image and its build
attestations (`SBOM`, provenance) with the
platform each one describes.

#### Examples

```bash

$ apolo image inspect image:/other-project/alpine:shared
$ apolo image inspect image:myimage:latest
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### ls

List images


#### Usage

```bash
apolo image ls [OPTIONS]
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



### pull

Pull an image from platform registry


#### Usage

```bash
apolo image pull [OPTIONS] REMOTE_IMAGE [LOCAL_IMAGE]
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
$ apolo pull --platform linux/amd64 image:myimage
$ apolo pull --platform linux/amd64 --platform linux/arm64 image:myimage
$ apolo pull --all-platforms image:myimage
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _--all-platforms_ | Pull all platforms of a multi-platform image. Requires the containerd image store. |
| _--platform PLATFORM_ | Pull the image for a specific platform, e.g. linux/amd64 \(multiple option, the docker engine platform by default\). Pulling several platforms requires the containerd image store. |



### push

Push an image to platform registry


#### Usage

```bash
apolo image push [OPTIONS] LOCAL_IMAGE [REMOTE_IMAGE]
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

Remove image from platform registry


#### Usage

```bash
apolo image rm [OPTIONS] IMAGES...
```

Remove image from platform registry.

Image name must be `URL` with image://
scheme.
Image name must contain tag.

#### Examples

```bash

$ apolo image rm image:/other-project/alpine:shared
$ apolo image rm image:myimage:latest
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-f_ | Force deletion of all tags referencing the image. |



### size

Get image size


#### Usage

```bash
apolo image size [OPTIONS] IMAGE
```

Get image size

Image name must be `URL` with image:// scheme.
Image name must
contain tag.

#### Examples

```bash

$ apolo image size image:/other-project/alpine:shared
$ apolo image size image:myimage:latest
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |



### tags

List tags for image in platform registry


#### Usage

```bash
apolo image tags [OPTIONS] IMAGE
```

List tags for image in platform registry.

Image name must be `URL` with
image:// scheme.

#### Examples

```bash

$ apolo image tags image:/other-project/alpine
$ apolo image tags -l image:myimage
```

#### Options

| Name | Description |
| :--- | :--- |
| _--help_ | Show this message and exit. |
| _-l_ | List in long format, with image sizes. |


