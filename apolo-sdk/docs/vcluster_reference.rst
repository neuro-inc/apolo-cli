==================
VCluster API Reference
==================


.. currentmodule:: apolo_sdk


VCluster
========

.. class:: VCluster

   Manages vcluster settings, in particular operates with service accounts.

   .. method:: create_service_account(name: str, *, cluster_name: str | None = None, org_name: str | None = None, project_name: str | None = None, ttl: datetime.timedelta = YEAR) -> str
      :async:

      Create a service account.

      :param str name: name of created service account. The name of underlying kubernetes object is combined from *name* and *user name*.
      :param str cluster_name: cluster to list applications. Default is current cluster.
      :param str org_name: org to list applications. Default is current org.
      :param str project_name: project to list applications. Default is current project.
      :param datetime.timedelta ttl: TTL of created object.

      :return str: generated kube config (YAML).

   .. method:: regenerate_service_account(name: str, *, cluster_name: str | None = None, org_name: str | None = None, project_name: str | None = None, ttl: datetime.timedelta = YEAR) -> str
      :async:

      Regenerate kube config a service account, reusing the previous name.

      :param str name: name of the service account.
      :param str cluster_name: cluster to list applications. Default is current cluster.
      :param str org_name: org to list applications. Default is current org.
      :param str project_name: project to list applications. Default is current project.
      :param datetime.timedelta ttl: TTL of created object.

      :return str: generated kube config (YAML).

   .. method:: activate_service_account(name: str, *, cluster_name: str | None = None, org_name: str | None = None, project_name: str | None = None) -> str
      :async:

      Activate previously generated kube config for service account. The config file should exist and located as ``~/.apolo/{cluster_name}/{org_name}/{project_mname}/{username}-{name}.yaml``.

      :param str name: name of the service account.
      :param str cluster_name: cluster to list applications. Default is current cluster.
      :param str org_name: org to list applications. Default is current org.
      :param str project_name: project to list applications. Default is current project.
      :return str: generated kube config (YAML).

   .. method:: list_service_accounts(*, cluster_name: str | None = None, org_name: str | None = None, project_name: str | None = None, all_users: bool = False) -> AsyncIterator[KubeServiceAccount]
      :async:

      Return a list of service accounts for the project.

      :param str cluster_name: cluster to list applications. Default is current cluster.
      :param str org_name: org to list applications. Default is current org.
      :param str project_name: project to list applications. Default is current project.
      :param bool all_users: return service accounts for all project's users, not for the current one only (off by default).

   .. method:: delete_service_accounts(name: str, *, cluster_name: str | None = None, org_name: str | None = None, project_name: str | None = None, all_users: bool = False) -> AsyncIterator[KubeServiceAccount]
      :async:

      Delete the service account.

      :param str name: name of the service account.
      :param str cluster_name: cluster to list applications. Default is current cluster.
      :param str org_name: org to list applications. Default is current org.
      :param str project_name: project to list applications. Default is current project.


.. class:: KubeServiceAccount

   *Read-only* :class:`~dataclasses.dataclass` for describing a kubernetes service account.

   .. attribute:: user

      The user name, :class:`str`.

   .. attribute:: name

      The service account name, :class:`str`.

   .. attribute:: created_at

      The creation timestamp, :class:`datetime.datetime`.

   .. attribute:: expired_at

      The expiration timestamp, :class:`datetime.datetime`.
