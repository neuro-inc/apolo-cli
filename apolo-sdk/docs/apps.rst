=================
Apps API Reference
=================


.. currentmodule:: apolo_sdk


Apps
====

.. class:: Apps

   Application management subsystem. Allows listing and uninstalling applications, as well as browsing available application templates.

   .. method:: list(cluster_name: Optional[str] = None, org_name: Optional[str] = None, project_name: Optional[str] = None) -> AsyncContextManager[AsyncIterator[App]]
      :async:

      List applications, async iterator. Yields :class:`App` instances.

      :param str cluster_name: cluster to list applications. Default is current cluster.
      :param str org_name: org to list applications. Default is current org.
      :param str project_name: project to list applications. Default is current project.

   .. method:: list_templates(cluster_name: Optional[str] = None) -> AsyncContextManager[AsyncIterator[AppTemplate]]
      :async:

      List available application templates, async iterator. Yields :class:`AppTemplate` instances.

      :param str cluster_name: cluster to list templates. Default is current cluster.

===

.. class:: App

   *Read-only* :class:`~dataclasses.dataclass` for describing application instance.

   .. attribute:: id

      The application ID, :class:`str`.

   .. attribute:: name

      The application name, :class:`str`.

   .. attribute:: display_name

      The application display name, :class:`str`.

   .. attribute:: template_name

      The template name used for the application, :class:`str`.

   .. attribute:: template_version

      The template version used for the application, :class:`str`.

   .. attribute:: project_name

      Project the application belongs to, :class:`str`.

   .. attribute:: org_name

      Organization the application belongs to, :class:`str`.

   .. attribute:: state

      Current state of the application, :class:`str`.

===

.. class:: AppTemplate

   *Read-only* :class:`~dataclasses.dataclass` for describing an application template.

   .. attribute:: name

      The template name, :class:`str`.

   .. attribute:: version

      Template version, :class:`str`.

   .. attribute:: short_description

      Short description of the template, :class:`str`.

   .. attribute:: tags

      List of template tags, :class:`list` of :class:`str`.
