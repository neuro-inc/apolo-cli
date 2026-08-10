=====================
Buckets API Reference
=====================


.. currentmodule:: apolo_sdk


Buckets
=======

.. class:: Buckets

   Blob storage buckets subsystems, available as :attr:`Client.buckets`.

   The subsystem helps take advantage of many basic functionality of Blob Storage
   solutions different cloud providers support. For AWS it would be S3, for GCP -
   Cloud Storage, etc.

   .. method:: list(cluster_name: Optional[str] = None) -> AsyncContextManager[AsyncIterator[Bucket]]
      :async:

      List user's buckets, async iterator. Yields :class:`Bucket` instances.

      :param str cluster_name: cluster to list buckets. Default is current cluster.

   .. method:: create(  \
                        name: typing.Optional[str], \
                        cluster_name: Optional[str] = None, \
                        org_name: Optional[str] = None, \
                 ) -> Bucket
      :async:

      Create a new bucket.

      :param ~typing.Optional[str] name: Name of the bucket. Should be unique among all user's
                                         bucket.

      :param str cluster_name: cluster to create a bucket. Default is current cluster.

      :param str org_name: org to create a bucket. Default is current org.


      :return: Newly created bucket info (:class:`Bucket`)

   .. method:: import_external(  \
                                 provider: Bucket.Provider, \
                                 provider_bucket_name: str, \
                                 credentials: Mapping[str, str], \
                                 name: Optional[str] = None, \
                                 cluster_name: Optional[str] = None, \
                                 org_name: Optional[str] = None, \
                 ) -> Bucket
      :async:

      Import a new bucket.


      :param Bucket.Provider provider: Provider type of imported bucket.

      :param str provider_bucket_name: Name of external bucket inside the provider.

      :param Mapping[str, str] credentials: Raw credentials to access bucket provider.

      :param ~typing.Optional[str] name: Name of the bucket. Should be unique among all user's
                                         bucket.

      :param str cluster_name: cluster to import a bucket. Default is current cluster.

      :param str org_name: org to import a bucket. Default is current org.


      :return: Newly imported bucket info (:class:`Bucket`)

   .. method:: get(bucket_id_or_name: str, cluster_name: Optional[str] = None, bucket_owner: Optional[str) = None) -> Bucket
      :async:

      Get a bucket with id or name *bucket_id_or_name*.

      :param str bucket_id_or_name: bucket's id or name.

      :param str cluster_name: cluster to look for a bucket. Default is current cluster.

      :param str bucket_owner: bucket owner's username. Used only if looking up for bucket by it's name.
                               Default is current user.

      :return: Bucket info (:class:`Bucket`)

   .. method:: rm(bucket_id_or_name: str, cluster_name: Optional[str] = None, bucket_owner: Optional[str) = None) -> None
      :async:

      Delete a bucket with id or name *bucket_id_or_name*.

      :param str bucket_id_or_name: bucket's id or name.

      :param str cluster_name: cluster to look for a bucket. Default is current cluster.

      :param str bucket_owner: bucket owner's username. Used only if looking up for bucket by it's name.
                               Default is current user.

   .. method:: request_tmp_credentials(bucket_id_or_name: str, cluster_name: Optional[str] = None, bucket_owner: Optional[str) = None) -> BucketCredentials
      :async:

      Get a temporary provider credentials to bucket with id or name *bucket_id_or_name*.

      :param str bucket_id_or_name: bucket's id or name.

      :param str cluster_name: cluster to look for a bucket. Default is current cluster.

      :param str bucket_owner: bucket owner's username. Used only if looking up for bucket by it's name.
                               Default is current user.

      :return: Bucket credentials info (:class:`BucketCredentials`)

   .. method:: set_public_access(bucket_id_or_name: str, public_access: bool, cluster_name: Optional[str] = None, bucket_owner: Optional[str) = None) -> Bucket
      :async:

      Enable or disable public (anonymous) read access to bucket.

      :param str bucket_id_or_name: bucket's id or name.

      :param str public_access: New public access setting.

      :param str cluster_name: cluster to look for a bucket. Default is current cluster.

      :param str bucket_owner: bucket owner's username. Used only if looking up for bucket by it's name.
                               Default is current user.

      :return: Bucket info (:class:`Bucket`)

   .. method:: head_blob(bucket_id_or_name: str, key: str, cluster_name: Optional[str] = None, bucket_owner: Optional[str) = None) -> BucketEntry
      :async:

      Look up the blob and return it's metadata.

      :param str bucket_id_or_name: bucket's id or name.
      :param str key: key of the blob.
      :param str cluster_name: cluster to look for a bucket. Default is current cluster.
      :param str bucket_owner: bucket owner's username. Used only if looking up for bucket by it's name.
                               Default is current user.

      :return: :class:`BucketEntry` object.

      :raises: :exc:`ResourceNotFound` if key does not exist.

   .. method:: put_blob(  \
                             bucket_id_or_name: str,  \
                             key: str,  \
                             body: Union[AsyncIterator[bytes], bytes], \
                             cluster_name: Optional[str] = None,  \
                             bucket_owner: Optional[str) = None,  \
                          ) -> None
      :async:

      Create or replace blob identified by ``key`` in the bucket, e.g::

         large_file = Path("large_file.dat")
         size = large_file.stat().st_size
         file_md5 = await calc_md5(large_file)

         async def body_stream():
             with large_file.open("r") as f:
                 for line in f:
                     yield f

         await client.buckets.put_blob(
             bucket_id_or_name="my_bucket",
             key="large_file.dat",
             body=body_stream,
         )

      :param str bucket_id_or_name: bucket's id or name.
      :param str key: Key of the blob.
      :param bytes body: Body of the blob. Can be passed as either :class:`bytes`
         or as an ``AsyncIterator[bytes]``.
      :param str cluster_name: cluster to look for a bucket. Default is current cluster.
      :param str bucket_owner: bucket owner's username. Used only if looking up for bucket by it's name.
                               Default is current user.

   .. method:: fetch_blob(  \
                             bucket_id_or_name: str,  \
                             key: str,  \
                             offset: int = 0, \
                             cluster_name: Optional[str] = None,  \
                             bucket_owner: Optional[str) = None,  \
                          ) -> AsyncIterator[bytes]
      :async:

      Look up the blob and return it's body content only. The content will be streamed
      using an asynchronous iterator, e.g.::

         async with client.buckets.fetch_blob("my_bucket", key="file.txt") as content:
             async for data in content:
                 print("Next chunk of data:", data)

      :param str bucket_id_or_name: bucket's id or name.
      :param str key: Key of the blob.
      :param int offset: Position in blob from which to read.
      :param str cluster_name: cluster to look for a bucket. Default is current cluster.
      :param str bucket_owner: bucket owner's username. Used only if looking up for bucket by it's name.
                               Default is current user.

   .. method:: delete_blob(bucket_id_or_name: str, key: str, cluster_name: Optional[str] = None, bucket_owner: Optional[str) = None) -> None
      :async:

      Remove blob from the bucket.

      :param str bucket_id_or_name: bucket's id or name.
      :param str key: key of the blob.
      :param str cluster_name: cluster to look for a bucket. Default is current cluster.
      :param str bucket_owner: bucket owner's username. Used only if looking up for bucket by it's name.
                               Default is current user.

   .. method:: list_blobs(uri: URL, \
                              recursive: bool = False, limit: int = 10000 \
                  ) -> AsyncContextManager[AsyncIterator[BucketEntry]]
      :async:

      List blobs in the bucket. You can filter by prefix and return results similar
      to a folder structure if ``recursive=False`` is provided.

      :param URL uri: URL that specifies bucket and prefix to list blobs,
                      e.g. ``yarl.URL("blob:bucket_name/path/in/bucket")``.
      :param recursive bool: If ``True`` listing will contain *all* keys filtered by
          prefix, while with ``False`` only ones up to next ``/`` will be returned.
          To indicate missing keys, all that were listed will be combined under a
          common prefix and returned as :class:`BlobCommonPrefix`.
      :param limit int: Maximum number of :class:`BucketEntry` objects returned.


   .. method:: glob_blobs(uri: URL) -> AsyncContextManager[AsyncIterator[BucketEntry]]
      :async:

      Glob search for blobs in the bucket::

          async with client.buckets.glob_blobs(
              uri=URL("blob:my_bucket/folder1/**/*.txt")
          ) as blobs:
              async for blob in blobs:
                  print(blob.key)

      Similar to :meth:`Storage.glob` the ``“**”`` pattern means “this directory and
      all sub-directories, recursively”.

      :param URL uri: URL that specifies bucket and pattern to glob blobs,
                      e.g. ``yarl.URL("blob:bucket_name/path/**/*.bin")``.

   .. method:: upload_file(src: URL, dst: URL, \
                             *, update: bool = False, \
                             progress: Optional[AbstractFileProgress] = None \
                 ) -> None:
      :async:

      Similarly to :meth:`Storage.upload_file`, allows to upload local file *src* to
      bucket URL *dst*.

      :param ~yarl.URL src: path to uploaded file on local disk,
                            e.g. ``yarl.URL("file:///home/andrew/folder/file.txt")``.

      :param ~yarl.URL dst: URL that specifies bucket and key to upload file
                            e.g. ``yarl.URL("blob:bucket_name/folder/file.txt")``.

      :param bool update: if true, upload only when the source file is newer
                          than the destination file or when the destination
                          file is missing.

      :param AbstractFileProgress progress:

         a callback interface for reporting uploading progress, ``None`` for no progress
         report (default).

   .. method:: download_file(src: URL, dst: URL, \
                               *, update: bool = False, \
                               continue_: bool = False, \
                               progress: Optional[AbstractFileProgress] = None \
                 ) -> None:
      :async:

      Similarly to :meth:`Storage.download_file`, allows to download remote file
      *src* to local path *dst*.

      :param ~yarl.URL src: URL that specifies bucket and blob key to download
                            e.g. ``yarl.URL("blob:bucket_name/folder/file.bin")``.

      :param ~yarl.URL dst: local path to save downloaded file,
                            e.g. ``yarl.URL("file:///home/andrew/folder/file.bin")``.

      :param bool update: if true, download only when the source file is newer
                          than the destination file or when the destination
                          file is missing.

      :param bool continue_: if true, download only the part of the source file
                             past the end of the destination file and append it
                             to the destination file if the destination file is
                             newer and not longer than the source file.
                             Otherwise download and overwrite the whole file.

      :param AbstractFileProgress progress:

         a callback interface for reporting downloading progress, ``None`` for
         no progress report (default).


   .. method:: upload_dir(src: URL, dst: URL, \
                            *, update: bool = False, \
                            filter: Optional[Callable[[str], Awaitable[bool]]] = None, \
                            ignore_file_names: AbstractSet[str] = frozenset(), \
                            progress: Optional[AbstractRecursiveFileProgress] = None \
                 ) -> None:
      :async:

      Similarly to :meth:`Storage.upload_dir`, allows to recursively upload local
      directory *src* to Blob Storage URL *dst*.


      :param ~yarl.URL src: path to uploaded directory on local disk,
                            e.g. ``yarl.URL("file:///home/andrew/folder")``.

      :param ~yarl.URL dst: path on Blob Storage for saving uploading directory
                            e.g. ``yarl.URL("blob:bucket_name/folder/")``.


      :param bool update: if true, download only when the source file is newer
                          than the destination file or when the destination
                          file is missing.

      :param Callable[[str], Awaitable[bool]] filter:

         a callback function for determining which files and subdirectories
         be uploaded. It is called with a relative path of file or directory
         and if the result is false the file or directory will be skipped.

      :param AbstractSet[str] ignore_file_names:

         a set of names of files which specify filters for skipping files and
         subdirectories. The format of ignore files is the same as
         ``.gitignore``.

      :param AbstractRecursiveFileProgress progress:

         a callback interface for reporting uploading progress, ``None`` for no progress
         report (default).

   .. method:: download_dir(src: URL, dst: URL, \
                              *, update: bool = False, \
                              continue_: bool = False, \
                              filter: Optional[Callable[[str], Awaitable[bool]]] = None, \
                              progress: Optional[AbstractRecursiveFileProgress] = None \
                 ) -> None:
      :async:

      Similarly to :meth:`Storage.download_dir`, allows to recursively download
      remote directory *src* to local path *dst*.

      :param ~yarl.URL src: path on Blob Storage to download a directory from
                            e.g. ``yarl.URL("blob:bucket_name/folder/")``.

      :param ~yarl.URL dst: local path to save downloaded directory,
                            e.g. ``yarl.URL("file:///home/andrew/folder")``.

      :param bool update: if true, download only when the source file is newer
                          than the destination file or when the destination
                          file is missing.

      :param bool continue_: if true, download only the part of the source file
                             past the end of the destination file and append it
                             to the destination file if the destination file is
                             newer and not longer than the source file.
                             Otherwise download and overwrite the whole file.

      :param Callable[[str], Awaitable[bool]] filter:

         a callback function for determining which files and subdirectories
         be downloaded. It is called with a relative path of file or directory
         and if the result is false the file or directory will be skipped.

      :param AbstractRecursiveFileProgress progress:

         a callback interface for reporting downloading progress, ``None`` for no
         progress report (default).

   .. method:: blob_is_dir(uri: URL) -> bool
      :async:

      Check weather *uri* specifies a "folder" blob in a bucket.

      :param ~yarl.URL src: URL that specifies bucket and blob key
                            e.g. ``yarl.URL("blob:bucket_name/folder/sub_folder")``.

   .. method:: blob_rm(uri: URL, *, recursive: bool = False, progress: Optional[AbstractDeleteProgress] = None) -> None
      :async:

      Remove blobs from bucket.

      :param ~yarl.URL uri: URL that specifies bucket and blob key
                            e.g. ``yarl.URL("blob:bucket_name/folder/sub_folder")``.

      :param bool recursive: remove a directory recursively with all nested files and
                             folders if ``True`` (``False`` by default).

      :param AbstractDeleteProgress progress:

         a callback interface for reporting delete progress, ``None`` for no progress
         report (default).

      :raises: :exc:`IsADirectoryError` if *uri* points on a directory and *recursive*
               flag is not set.

   .. method:: make_signed_url(uri: URL, expires_in_seconds: int = 3600) -> URL
      :async:

      Generate a singed url that allows temporary access to blob.

      :param ~yarl.URL uri: URL that specifies bucket and blob key
                            e.g. ``yarl.URL("blob:bucket_name/folder/file.bin")``.

      :param int expires_in_seconds: Duration in seconds generated url will be valid.

      :return: Signed url (:class:`yarl.URL`)

   .. method:: get_disk_usage(bucket_id_or_name: str, \
                                cluster_name: Optional[str] = None, \
                                bucket_owner: Optional[str) = None, \
                 ) -> AsyncContextManager[AsyncIterator[BucketUsage]]
      :async:

      Get disk space usage of a given bucket. Iterator yield partial results as calculation
      for the whole bucket can take time.

      :param str bucket_id_or_name: bucket's id or name.
      :param str cluster_name: cluster to look for a bucket. Default is current cluster.
      :param str bucket_owner: bucket owner's username. Used only if looking up for bucket by it's name.
                               Default is current user.

   .. method:: persistent_credentials_list(cluster_name: Optional[str] = None) -> AsyncContextManager[AsyncIterator[PersistentBucketCredentials]]
      :async:

      List user's bucket persistent credentials, async iterator. Yields :class:`PersistentBucketCredentials` instances.

      :param str cluster_name: cluster to list persistent credentials. Default is current cluster.

   .. method:: persistent_credentials_create(  \
                        bucket_ids: typing.Iterable[str], \
                        name: typing.Optional[str], \
                        read_only: Optional[bool] = False, \
                        cluster_name: Optional[str] = None, \
                 ) -> PersistentBucketCredentials
      :async:

      Create a new persistent credentials for given set of buckets.

      :param ~typing.Iterable[str] bucket_ids: Iterable of bucket ids to create credentials for.

      :param ~typing.Optional[str] name: Name of the persistent credentials. Should be unique among all user's
                                         bucket persistent credentials.

      :param str read_only: Allow only read-only access using created credentials. ``False`` by default.

      :param str cluster_name: cluster to create a persistent credentials. Default is current cluster.


      :return: Newly created credentials info (:class:`PersistentBucketCredentials`)

   .. method:: persistent_credentials_get(credential_id_or_name: str, cluster_name: Optional[str] = None) -> PersistentBucketCredentials
      :async:

      Get a persistent credentials with id or name *credential_id_or_name*.

      :param str credential_id_or_name: persistent credentials's id or name.

      :param str cluster_name: cluster to look for a persistent credentials. Default is current cluster.

      :return: Credentials info (:class:`PersistentBucketCredentials`)

   .. method:: persistent_credentials_rm(credential_id_or_name: str, cluster_name: Optional[str] = None) -> None
      :async:

      Delete a persistent credentials with id or name *credential_id_or_name*.

      :param str credential_id_or_name: persistent credentials's id or name.

      :param str cluster_name: cluster to look for a persistent credentials. Default is current cluster.

Bucket
======

.. class:: Bucket

   *Read-only* :class:`~dataclasses.dataclass` for describing single bucket.

   .. attribute:: id

      The bucket id, :class:`str`.

   .. attribute:: owner

      The bucket owner username, :class:`str`.

   .. attribute:: name

      The bucket name set by user, unique among all user's buckets,
      :class:`str` or ``None`` if no name was set.

   .. attribute:: uri

      URI of the bucket resource, :class:`yarl.URL`.

   .. attribute:: cluster_name

      Cluster this bucket belongs to, :class:`str`.

   .. attribute:: org_name

      Org this bucket belongs to, :class:`str` or `None` if there is no such org.

   .. attribute:: created_at

      Bucket creation timestamp, :class:`~datetime.datetime`.

   .. attribute:: provider

      Blob storage provider this bucket belongs to, :class:`Bucket.Provider`.


BucketCredentials
=================

.. class:: BucketCredentials

   *Read-only* :class:`~dataclasses.dataclass` for describing credentials to single bucket.

   .. attribute:: bucket_id

      The bucket id, :class:`str`.

   .. attribute:: provider

      Blob storage provider this bucket belongs to, :class:`Bucket.Provider`.

   .. attribute:: credentials

      Raw credentials to access a bucket inside the provider, :class:`Mapping[str, str]`


Bucket.Provider
===============

.. class:: Bucket.Provider

   *Enumeration* that describes bucket providers.

   Can be one of the following values:

   .. attribute:: AWS

      Amazon Web Services S3 bucket

   .. attribute:: MINIO

      Minio S3 bucket

   .. attribute:: SEAWEEDFS

      SeaweedFS S3-compatible bucket

   .. attribute:: AZURE

      Azure blob storage container


PersistentBucketCredentials
===========================

.. class:: PersistentBucketCredentials

   *Read-only* :class:`~dataclasses.dataclass` for describing persistent credentials to some set of buckets
   created after user request.

   .. attribute:: id

      The credentials id, :class:`str`.

   .. attribute:: owner

      The credentials owner username, :class:`str`.

   .. attribute:: name

      The credentials name set by user, unique among all user's bucket credentials,
      :class:`str` or ``None`` if no name was set.

   .. attribute:: read_only

      The credentials provide read-only access to buckets, :class:`bool`.

   .. attribute:: cluster_name

      Cluster this credentials belongs to, :class:`str`.

   .. attribute:: credentials

      List of per bucket credentials, :class:`List[BucketCredentials]`


BucketEntry
===========

.. class:: BucketEntry

   An abstract class :class:`~dataclasses.dataclass` for describing bucket contents entries.

   .. attribute:: key

      Key of the blob, :class:`str`.

   .. attribute:: bucket

      Containing bucket, :class:`Bucket`.

   .. attribute:: size

      Size of the data in *bytes*, :class:`int`.

   .. attribute:: created_at

      Blob creation timestamp, :class:`~datetime.datetime` or ``None``
      if underlying blob engine do not store such information

   .. attribute:: modified_at

      Blob modification timestamp, :class:`~datetime.datetime` or ``None``
      if underlying blob engine do not store such information

   .. attribute:: uri

      URI identifying the blob, :class:`~yarl.URL`, e.g.
      ``blob://cluster_name/username/my_bucket/file.txt``.

   .. attribute:: name

      Name of blob, part of key after last ``/``, :class:`str`

   .. method:: is_dir(uri: URL) -> bool

      ``True`` if entry is directory blob object

   .. method:: is_file(uri: URL) -> bool

      ``True`` if entry is file blob object


BlobObject
==========

.. class:: BlobObject

   An ancestor of :class:`BucketEntry` used for key that are present directly in underlying blob storage.


BlobCommonPrefix
================

.. class:: BlobCommonPrefix

   An ancestor of :class:`BucketEntry` for describing common prefixes for
   blobs in non-recursive listing. You can treat it as a kind of *folder* on Blob
   Storage.


BucketUsage
===========

.. class:: BucketUsage

   An :class:`~dataclasses.dataclass` for describing bucket disk space usage.

   .. attribute:: total_bytes

      Total size of all objects in bytes, :class:`int`.

   .. attribute:: object_count

      Total number of objects, :class:`int`.
