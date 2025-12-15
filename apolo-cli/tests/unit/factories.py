from apolo_sdk import App


def _app_factory(
    id: str = "app-123",
    name: str = "test-app-1",
    display_name: str = "Test App 1",
    template_name: str = "test-template",
    template_version: str = "1.0",
    cluster_name: str = "test-cluster",
    project_name: str = "test-project",
    org_name: str = "test-org",
    namespace: str = "",
    state: str = "running",
    creator: str = "test-user",
    created_at: str = "2025-05-07T11:00:00+00:00",
    updated_at: str = "2025-05-07T11:00:00+00:00",
    endpoints: list[str] = [],
) -> App:
    return App(**locals())
