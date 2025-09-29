=====================
Secrets API Reference
=====================


.. currentmodule:: apolo_sdk


Secrets
=======

.. class:: Secrets

   Secured secrets subsystems.  Secrets can be passed as mounted files and environment
   variables into a running job.

   .. method:: list(cluster_name: Optional[str] = None, org_name: Optional[str] = None) -> AsyncContextManager[AsyncIterator[Secret]]
      :async:

      List user's secrets, async iterator. Yields :class:`Secret` instances.

      :param str cluster_name: cluster to list secrets. Default is current cluster.
      :param str org_name: org to list secrets. Default is current org.

   .. method:: add(key: str, value: bytes, cluster_name: Optional[str] = None, org_name: Optional[str] = None) -> None
      :async:

      Add a secret with name *key* and content *value*.

      :param str key: secret's name.

      :param bytes vale: secret's value.

      :param str cluster_name: cluster to create a secret. Default is current cluster.
      :param str org_name: org to create a secrets. Default is current org.

   .. method:: get(key: str, cluster_name: Optional[str] = None, org_name: Optional[str] = None, project_name: Optional[str] = None) -> bytes
      :async:

      Get a secret *key* value.

      :param str key: secret's name.

      :param str cluster_name: cluster to look for a secret. Default is current cluster.
      :param str org_name: org to look for a secrets. Default is current org.
      :param str project_name: project to look for a secrets. Default is current project.

      :return: The secret value as bytes.

   .. method:: rm(key: str, cluster_name: Optional[str] = None, org_name: Optional[str] = None) -> None
      :async:

      Delete a secret *key*.

      :param str key: secret's name.

      :param str cluster_name: cluster to look for a secret. Default is current cluster.
      :param str org_name: org to look for a secrets. Default is current org.


Secret
======

.. class:: Secret

   *Read-only* :class:`~dataclasses.dataclass` for describing secret instance.

   .. attribute:: key

      The secret key, :class:`str`.

   .. attribute:: owner

      The secret owner username, :class:`str`.

   .. attribute:: cluster_name

      Cluster secret resource belongs to, :class:`str`.


   .. attribute:: org_name

      Org secret resource belongs to, :class:`str` or `None` if there is no such org.

   .. attribute:: uri

      URI of the secret resource, :class:`yarl.URL`.
