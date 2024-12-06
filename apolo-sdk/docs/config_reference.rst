.. currentmodule:: apolo_sdk


.. _config-reference:

===========================
Configuration API Reference
===========================


API functions
=============

.. function:: find_project_root(path: Optional[Path] = None) -> Path

   Look for project root directory.

   Folder is considered a project root when it
   contains ``.neuro.toml``. Search begins at **path** or :meth:`Path.cwd` (current
   working directory) when **path** is **None** and checks all parent folders sequentially.
   Will raise an :class:`ConfigError` if search reaches root directory.


Config
======

.. class:: Config

   Configuration subsystem, available as :attr:`Client.config`.

   Use it for analyzing fetching information about the system configuration, e.g. a list
   of available clusters or switching the active cluster.

   .. attribute:: username

      User name used for working with Apolo Platform, read-only :class:`str`.

   .. attribute:: presets

      A :class:`typing.Mapping` of preset name (:class:`str`) to
      :class:`Preset` dataclass for the current cluster.

   .. attribute:: clusters

      A :class:`typing.Mapping` of cluster name (:class:`str`) to
      :class:`Cluster` dataclass for available clusters.

   .. attribute:: cluster_name

      The current cluster name, read-only :class:`str`.

      To switch on another cluster use :meth:`switch_cluster`.


   .. attribute:: org_name

      The current org name, read-only :class:`str`.

      To switch on another org use :meth:`switch_org`.

   .. method:: fetch() -> None
      :async:

      Fetch available clusters configuration from the Apolo Platform.

      .. note::

         The call updates local configuration files.

   .. method:: switch_cluster(name: str) -> None
      :async:

      Switch the current cluster to *name*.

      .. note::

         The call updates local configuration files.

   .. method:: switch_org(name: str) -> None
      :async:

      Switch the current org to *name*.

      .. note::

         The call updates local configuration files.

   *Miscellaneous helpers*

   .. attribute:: api_url

      The Apolo Platform URL, :class:`yarl.URL`.

   .. attribute:: registry_url

      Docker Registry URL for the cluster, :class:`yarl.URL`.

      :attr:`Cluster.registry_url` for the current cluster.

   .. attribute:: storage_url

      Storage URL for the cluster, :class:`yarl.URL`.

      :attr:`Cluster.storage_url` for the current cluster.

   .. attribute:: monitoring_url

      Monitoring URL for the cluster, :class:`yarl.URL`.

      :attr:`Cluster.monitoring_url` for the current cluster.

   .. method:: get_user_config() -> Mapping[str, Any]
      :async:

      Return user-provided config dictionary. Config is loaded from config files.
      There are two configuration files: **global** and **local**, both are optional
      and can be absent.

      The global file is named ``user.toml`` and the API search for it in the path
      provided to :class:`Factory` or :func:`get` (``$HOME/.neuro/user.toml`` by default).

      The local config file is named ``.neuro.toml``, and the API search for this file
      starting from the current folder up to the root directory.

      Found local and global configurations are merged.
      If a parameter is present are both global and local versions the local parameter
      take a precedence.

      Configuration files have a TOML format (a stricter version of well-known INI
      format). See https://en.wikipedia.org/wiki/TOML and
      https://github.com/toml-lang/toml#toml for the format specification details.

      The API will raise an :class:`ConfigError` if configuration files contains unknown sections or parameters.
      Note that currently API doesn't use any parameter from user config.

      Known sections: **alias**, **job**, **storage**.

      Section **alias** can have any subsections with any keys.

      Section **job** can have following keys: **ps-format** - string, **life-span** - string.

      Section **storage** can have following keys: **cp-exclude** - list of strings,
      **cp-exclude-from-files** - list of strings.

      There is a plugin system that allows to register additional config parameters. To
      define a plugin, add a **apolo_api** entrypoint (check
      https://packaging.python.org/specifications/entry-points/ for more info about entry points).
      Entry point should be callable with single argument of type :class:`PluginManager`.

      .. versionadded:: 20.01.15

   .. method:: token() -> str
      :async:

      *Bearer* token to log into the Apolo Platform.

      The token expires after some period, the call automatically refreshes the token if
      needed.


Cluster
=======

.. class:: Cluster


   *Read-only* :class:`~dataclasses.dataclass` for describing a cluster configuration.

   Clusters are loaded on login to the Apolo platform and updated on
   :meth:`Config.fetch` call.

   :meth:`Config.switch_cluster` changes the active cluster.

   .. attribute:: name

      Cluster name, :class:`str`.

   .. attribute:: registry_url

      Docker Registry URL for the cluster, :class:`yarl.URL`.

   .. attribute:: storage_url

      Storage URL for the cluster, :class:`yarl.URL`.

   .. attribute:: users_url

      Users URL for the cluster, :class:`yarl.URL`.

   .. attribute:: monitoring_url

      Monitoring URL for the cluster, :class:`yarl.URL`.

   .. attribute:: presets

      A :class:`typing.Mapping` of available job resource presets, keys are preset names
      (:class:`str`), values are :class:`Preset` objects.

   .. attribute:: apps

      A :class:`AppsConfig` object, representing platform applications configuration in the cluster.

Preset
======

.. class:: Preset


   *Read-only* :class:`~dataclasses.dataclass` for describing a job configuration
   provided by Apolo Platform.

   Presets list is loaded on login to the Apolo platform and depends on used
   cluster.

   .. attribute:: cpu

      Requested number of CPUs, :class:`float`. Please note, Docker supports fractions
      here, e.g. ``0.5`` CPU means a half or CPU on the target node.

   .. attribute:: memory_mb

      Requested memory amount in MegaBytes, :class:`int`.

   .. attribute:: is_preemptible

      A flag that specifies is the job is *preemptible* or not, see :ref:`Preemption
      <job-preemption>` for details.

   .. attribute:: gpu

      The number of requested GPUs, :class:`int`. Use ``None`` for jobs that doesn't
      require GPU.

   .. attribute:: gpu_model

      The name of requested GPU model, :class:`str` (or ``None`` for job without GPUs).

   .. attribute:: tpu_type

      Requested TPU type, see also https://en.wikipedia.org/wiki/Tensor_processing_unit

   .. attribute:: tpu_software_version

      Requested TPU software version.


AppsConfig
==========

.. class:: AppsConfig

   *Read-only* :class:`~dataclasses.dataclass` for describing applications configuration within the cluster
   provided by Apolo Platform.

   Applications configurations are loaded on login to the Apolo platform and depends on the used
   cluster.

   .. attribute:: hostname_templates

      Represent application ingress hostname templates, :class:`list[str]`. Empty :class:`list` by default.
      The hostname templates are defined and controlled by the cluster administrators and should be used when creating ingress resources for applications.
