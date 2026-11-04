====================
Images API Reference
====================


.. currentmodule:: apolo_sdk


Images
======

.. class:: Images

   Docker image subsystem.

   Used for pushing docker images onto Apolo docker registry for later usage by
   :meth:`Jobs.run` and pulling these images back to local docker.

   .. method:: push(local: LocalImage, \
                      remote: Optional[RemoteImage] = None, \
                      *, \
                      progress: Optional[AbstractDockerImageProgress] = None, \
                 ) -> RemoteImage
      :async:


      Push *local* docker image to *remote* side.

      :param LocalImage local: a spec of local docker image (e.g. created by ``docker
                               build``) for pushing on Apolo Registry.

      :param RemoteImage remote: a spec for remote image on Apolo
                                 Registry. Calculated from *local* image automatically
                                 if ``None`` (default).

      :param AbstractDockerImageProgress progress:

         a callback interface for reporting pushing progress, ``None`` for no progress
         report (default).

      :return: *remote* image if explicitly specified, calculated remote image if
               *remote* is ``None`` (:class:`RemoteImage`)


   .. method:: pull(remote: Optional[RemoteImage] = None, \
                      local: LocalImage, \
                      *, \
                      progress: Optional[AbstractDockerImageProgress] = None, \
                      platform: Union[str, Sequence[str], None] = None, \
                      all_platforms: bool = False, \
                 ) -> RemoteImage
      :async:

      Pull *remote* image from Apolo registry to *local* docker side.

      :param RemoteImage remote: a spec for remote image on Apolo
                                 registry.

      :param LocalImage local: a spec of local docker image to pull. Calculated from
                                 *remote* image automatically if ``None`` (default).


      :param AbstractDockerImageProgress progress:

         a callback interface for reporting pulling progress, ``None`` for no progress
         report (default).

      :param platform: platform to pull in the ``os[/arch[/variant]]`` format,
                       e.g. ``"linux/amd64"``, or a sequence of platforms to pull
                       one after another into the same *local* image. ``None``
                       means the platform of the docker engine (default).

                       Pulling several platforms requires the containerd image
                       store in the docker engine, :class:`ValueError` is raised
                       otherwise. The tag is resolved to its digest once, so all
                       platforms come from the same image even if the tag is
                       moved during the pull.

      :param bool all_platforms: pull every platform image of a multi-platform
                                 *remote* image, ``False`` by default. Cannot be
                                 combined with *platform*. :class:`ValueError` is
                                 raised if the image index has a platform image
                                 without a platform.

      :return: *local* image if explicitly specified, calculated remote image if
               *local* is ``None`` (:class:`LocalImage`)

   .. method:: digest(image: RemoteImage) -> str
      :async:

      Get digest of an image in Apolo registry.

      :param RemoteImage image: a spec for remote image on Apolo
                                 registry.


      :return: string representing image digest

   .. method:: rm(image: RemoteImage, digest: str) -> str
      :async:

      Delete remote image specified by given reference and digest from Apolo registry.

      :param RemoteImage image: a spec for remote image on Apolo
                                 registry.

      :param str digest: remote image digest, which can be obtained via `digest` method.



   .. method:: list(cluster_name: Optional[str] = None) -> List[RemoteImage]
      :async:

      List images on Apolo registry available to the user.

      :param str cluster_name: name of the cluster.

                               ``None`` means the current cluster (default).

      :return: list of remote images not including tags
               (:class:`List[RemoteImage]`)


   .. method:: tags(image: RemoteImage) -> List[RemoteImage]
      :async:

      List image references with tags for the specified remote *image*.

      :param RemoteImage image: a spec for remote image without tag on Apolo
                                registry.

      :return: list of remote images with tags (:class:`List[RemoteImage]`)


   .. method:: size(image: RemoteImage) -> int
      :async:

      Return image size.

      For a multi-platform image (an image index or a manifest list) the size is
      the total size of unique layers across all platform images, attestation
      manifests and other attached artifacts are not counted. A tag that references
      an artifact (e.g. an SBOM or a signature) has size 0.

      :param RemoteImage image: a spec for remote image with tag on Apolo
                                registry.

      :return: remote image size in bytes


   .. method:: tag_info(image: RemoteImage) -> Tag
      :async:

      Return info about specified tag.

      :param RemoteImage image: a spec for remote image with tag on Apolo
                                registry.

      :return: tag information (name and size) (:class:`Tag`)


   .. method:: inspect(image: RemoteImage) -> ImageInfo
      :async:

      Return the platform images and the attestations (e.g. SBOM and provenance
      produced by ``docker buildx build --sbom --provenance``) of specified tag.

      :param RemoteImage image: a spec for remote image with tag on Apolo
                                registry.

      :return: image information (:class:`ImageInfo`)


AbstractDockerImageProgress
===========================

.. class:: AbstractDockerImageProgress

   Base class for image operations progress, e.g. :meth:`Images.pull` and
   :meth:`Images.push`. Inherited from :class:`abc.ABC`.

   .. method:: pull(data: ImageProgressPull) -> None

      Pulling image from remote Apolo registry to local Docker is started.

      :param ImageProgressPull data: additional data, e.g. local and remote image
                                     objects.


   .. method:: push(data: ImageProgressPush) -> None

      Pushing image from local Docker to remote Apolo registry is started.

      :param ImageProgressPush data: additional data, e.g. local and remote image
                                     objects.

   .. method:: step(data: ImageProgressStep) -> None

      Next step in image transfer is performed.

      :param ImageProgressStep data: additional data, e.g. image layer id and progress
                                     report.

ImageProgressPull
=================

.. class:: ImageProgressPull

   *Read-only* :class:`~dataclasses.dataclass` for pulling operation report.

   .. attribute:: src

      Source image, :class:`RemoteImage` instance.

   .. attribute:: dst

      Destination image, :class:`LocalImage` instance.


.. class:: ImageProgressPush

   *Read-only* :class:`~dataclasses.dataclass` for pulling operation report.

   .. attribute:: src

      Source image, :class:`LocalImage` instance.

   .. attribute:: dst

      Destination image, :class:`RemoteImage` instance.


.. class:: ImageProgressStep

   *Read-only* :class:`~dataclasses.dataclass` for push/pull progress step.

   .. attribute:: layer_id

      Image layer, :class:`str`.

   .. attribute:: message

      Progress message, :class:`str`.


LocalImage
==========

.. class:: LocalImage

   *Read-only* :class:`~dataclasses.dataclass` for describing *image* in local Docker
   system.

   .. attribute:: name

      Image name, :class:`str`.

   .. attribute:: tag

      Image tag (:class:`str`), ``None`` if the tag is omitted (implicit ``latest``
      tag).


RemoteImage
===========

.. class:: RemoteImage

   *Read-only* :class:`~dataclasses.dataclass` for describing *image* in remote
   registry (Apolo Platform hosted or other registries like DockerHub_).

   .. attribute:: name

      Image name, :class:`str`.

   .. attribute:: tag

      Image tag (:class:`str`), ``None`` if the tag is omitted (implicit ``latest``
      tag).

   .. attribute:: owner

      User name (:class:`str`) of a person who manages this image.

      Public DockerHub_ images (e.g. ``"ubuntu:latest"``) have no *owner*, the attribute
      is ``None``.

   .. attribute:: org_name

      Name (:class:`str`) of an organization who manages this image  or `None`
      if there is no such org.

      Public DockerHub_ images (e.g. ``"ubuntu:latest"``) have no *org*, the attribute
      is ``None``.

   .. attribute:: registry

      Host name for images hosted on Apolo Registry (:class:`str`), ``None`` for
      other registries like DockerHub_.

    .. method:: as_docker_url(with_scheme: bool = False) -> str

      URL that can be used to reference this image with Docker.

      :param bool with_scheme: if set to True, returned URL includes scheme (`https://`), otherwise (default behavior) - scheme is omitted.

    .. method:: with_tag(tag: bool) -> RemoteImage

       Creates a new reference to remote image with *tag*.

       :param str tag: new tag

       :return: remote image with *tag*

    .. py:classmethod:: new_platform_image(name: str, registry: str, *, owner: str, cluster_name: str, tag: Optional[str] = None) -> RemoteImage

        Create a new instance referring to an image hosted on Apolo Platform.

      :param str name: name of the image

      :param str registry: registry where the image is located

      :param str owner: image owner name

      :param str cluster_name: name of the cluster

      :param str tag: image tag

    .. py:classmethod:: new_external_image(name: str, registry: Optional[str] = None, *, tag: Optional[str] = None) -> RemoteImage

        Create a new instance referring to an image hosted on an external registry (e.g. DockerHub_).

      :param str name: name of the image

      :param str registry: registry where the image is located

      :param str tag: image tag


.. class:: Tag

   *Read-only* :class:`~dataclasses.dataclass` for tag information.

   .. attribute:: name

      Tag name, :class:`str`.

   .. attribute:: size

      Tag size in bytes, :class:`int`.


ImageInfo
=========

.. class:: ImageInfo

   *Read-only* :class:`~dataclasses.dataclass` for image information returned by
   :meth:`Images.inspect`.

   .. attribute:: name

      Tag name, :class:`str`.

   .. attribute:: digest

      Digest of the tag manifest, :class:`str`.

   .. attribute:: media_type

      Media type of the tag manifest, e.g. an image index or an image manifest,
      :class:`str`.

   .. attribute:: size

      Image size in bytes, the same as :meth:`Images.size`, :class:`int`.

   .. attribute:: platforms

      Platform images, a sequence of :class:`ImagePlatform`.

   .. attribute:: attestations

      Attestations and other artifacts attached to the image, a sequence of
      :class:`ImageAttestation`.


ImagePlatform
=============

.. class:: ImagePlatform

   *Read-only* :class:`~dataclasses.dataclass` for a platform image.

   .. attribute:: digest

      Manifest digest, :class:`str`.

   .. attribute:: platform

      Platform in the ``os/arch[/variant]`` format, e.g. ``"linux/amd64"``,
      ``None`` for a single-platform image that is not an image index.

   .. attribute:: size

      Total size of the image layers in bytes, :class:`int`.


ImageAttestation
================

.. class:: ImageAttestation

   *Read-only* :class:`~dataclasses.dataclass` for an attestation manifest.

   .. attribute:: digest

      Manifest digest, :class:`str`.

   .. attribute:: type

      ``vnd.docker.reference.type`` annotation (``"attestation-manifest"``) or
      the OCI artifact type, ``None`` if unknown.

   .. attribute:: reference_digest

      Digest of the manifest the attestation describes, ``None`` if unknown.

   .. attribute:: predicate_types

      In-toto predicate types of the attestation layers, e.g.
      ``"https://spdx.dev/Document"`` or ``"https://slsa.dev/provenance/v1"``,
      a sequence of :class:`str`.

   .. attribute:: size

      Total size of the attestation layers in bytes, :class:`int`.


.. _DockerHub: https://hub.docker.com
