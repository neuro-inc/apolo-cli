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

   .. method:: list_templates(cluster_name: Optional[str] = None, org_name: Optional[str] = None, project_name: Optional[str] = None) -> AsyncContextManager[AsyncIterator[AppTemplate]]
      :async:

      List available application templates, async iterator. Yields :class:`AppTemplate` instances.

      :param str cluster_name: cluster to list templates. Default is current cluster.
      :param str org_name: org to list templates. Default is current org.
      :param str project_name: project to list templates. Default is current project.

   .. method:: list_template_versions(name: str, cluster_name: Optional[str] = None, org_name: Optional[str] = None, project_name: Optional[str] = None) -> AsyncContextManager[AsyncIterator[AppTemplate]]
      :async:

      List all available versions for a specific app template, async iterator. Yields :class:`AppTemplate` instances.

      :param str name: The name of the app template.
      :param str cluster_name: cluster to list template versions. Default is current cluster.
      :param str org_name: org to list template versions. Default is current org.
      :param str project_name: project to list template versions. Default is current project.

   .. method:: get_values(app_id: Optional[str] = None, value_type: Optional[str] = None, cluster_name: Optional[str] = None, org_name: Optional[str] = None, project_name: Optional[str] = None) -> AsyncContextManager[AsyncIterator[AppValue]]
      :async:

      Get values from app instances, async iterator. Yields :class:`AppValue` instances.

      :param str app_id: Optional app instance ID to filter values.
      :param str value_type: Optional value type to filter.
      :param str cluster_name: cluster to get values from. Default is current cluster.
      :param str org_name: org to get values from. Default is current org.
      :param str project_name: project to get values from. Default is current project.

   .. method:: logs(app_id: str, *, cluster_name: Optional[str] = None, org_name: Optional[str] = None, project_name: Optional[str] = None, since: Optional[datetime] = None, timestamps: bool = False) -> AsyncContextManager[AsyncIterator[bytes]]
      :async:

      Get logs for an app instance, async iterator. Yields chunks of logs as :class:`bytes`.

      :param str app_id: The ID of the app instance.
      :param str cluster_name: Cluster where the app is deployed. Default is current cluster.
      :param str org_name: Organization where the app is deployed. Default is current org.
      :param str project_name: Project where the app is deployed. Default is current project.
      :param datetime since: Optional timestamp to start logs from.
      :param bool timestamps: Include timestamps in the logs output.

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

===

.. class:: AppValue

   *Read-only* :class:`~dataclasses.dataclass` for describing an application value.

   .. attribute:: app_instance_id

      The application instance ID, :class:`str`.

   .. attribute:: type

      The value type, :class:`str`.

   .. attribute:: path

      The value path, :class:`str`.

   .. attribute:: value

      The actual value, can be any type.
