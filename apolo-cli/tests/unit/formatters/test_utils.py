import pytest
from yarl import URL

from apolo_cli.formatters.utils import uri_formatter


@pytest.mark.parametrize("scheme", ("storage", "image"))
def test_uri_formatter_without_org(scheme: str) -> None:
    fmtr = uri_formatter(
        project_name="test-project", cluster_name="cluster", org_name=None
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/test-project/path/to/file"))
        == f"{scheme}:path/to/file"
    )
    assert fmtr(URL(f"{scheme}://cluster/test-project/")) == f"{scheme}:"
    assert fmtr(URL(f"{scheme}://cluster/test-project")) == f"{scheme}:"
    assert fmtr(URL(f"{scheme}://cluster/")) == f"{scheme}:/"
    assert fmtr(URL(f"{scheme}://cluster")) == f"{scheme}:/"
    assert (
        fmtr(URL(f"{scheme}://cluster/other-project/path/to/file"))
        == f"{scheme}:/other-project/path/to/file"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/org/test-project/path/to/file"))
        == f"{scheme}:/org/test-project/path/to/file"
    )
    assert (
        fmtr(URL(f"{scheme}://othercluster/test-project/path/to/file"))
        == f"{scheme}://othercluster/test-project/path/to/file"
    )
    assert fmtr(URL("user://cluster/user/rest")) == "user://cluster/user/rest"


@pytest.mark.parametrize("scheme", ("storage", "image"))
def test_uri_formatter_with_org(scheme: str) -> None:
    fmtr = uri_formatter(
        project_name="test-project", cluster_name="cluster", org_name="org"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/org/test-project/path/to/file"))
        == f"{scheme}:path/to/file"
    )
    assert fmtr(URL(f"{scheme}://cluster/org/test-project/")) == f"{scheme}:"
    assert fmtr(URL(f"{scheme}://cluster/org/test-project")) == f"{scheme}:"
    assert fmtr(URL(f"{scheme}://cluster/org/")) == f"{scheme}:/"
    assert fmtr(URL(f"{scheme}://cluster/org")) == f"{scheme}:/"
    assert fmtr(URL(f"{scheme}://cluster/")) == f"{scheme}://cluster/"
    assert fmtr(URL(f"{scheme}://cluster")) == f"{scheme}://cluster"
    assert (
        fmtr(URL(f"{scheme}://cluster/test-project/path/to/file"))
        == f"{scheme}://cluster/test-project/path/to/file"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/org/other-project/path/to/file"))
        == f"{scheme}:/other-project/path/to/file"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/otherorg/test-project/path/to/file"))
        == f"{scheme}://cluster/otherorg/test-project/path/to/file"
    )
    assert (
        fmtr(URL(f"{scheme}://othercluster/org/test-project/path/to/file"))
        == f"{scheme}://othercluster/org/test-project/path/to/file"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/test-project/path/to/file"))
        == f"{scheme}://cluster/test-project/path/to/file"
    )
    assert (
        fmtr(URL("user://cluster/org/test-project/rest"))
        == "user://cluster/org/test-project/rest"
    )


@pytest.mark.parametrize("org_name", (None, "org"))
def test_global_uri_formatter(org_name: str | None) -> None:
    fmtr = uri_formatter(
        project_name="test-project", cluster_name="cluster", org_name=org_name
    )
    assert fmtr(URL("user://cluster/user/rest")) == "user://cluster/user/rest"
    assert fmtr(URL("user://cluster/org/user/rest")) == "user://cluster/org/user/rest"


@pytest.mark.parametrize("scheme", ("storage", "image"))
def test_uri_formatter_special_chars_without_org(scheme: str) -> None:
    fmtr = uri_formatter(
        project_name="test-project", cluster_name="cluster", org_name=None
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/test-project/путь/к/файлу"))
        == f"{scheme}:%D0%BF%D1%83%D1%82%D1%8C/%D0%BA/%D1%84%D0%B0%D0%B9%D0%BB%D1%83"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/other-project/путь/к/файлу"))
        == f"{scheme}:/other-project/"
        "%D0%BF%D1%83%D1%82%D1%8C/%D0%BA/%D1%84%D0%B0%D0%B9%D0%BB%D1%83"
    )
    assert (
        fmtr(URL(f"{scheme}://othercluster/test-project/путь/к/файлу"))
        == f"{scheme}://othercluster/test-project/"
        "%D0%BF%D1%83%D1%82%D1%8C/%D0%BA/%D1%84%D0%B0%D0%B9%D0%BB%D1%83"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/test-project/%2525%3f%23"))
        == f"{scheme}:%2525%3F%23"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/other-project/%2525%3f%23"))
        == f"{scheme}:/other-project/%2525%3F%23"
    )
    assert (
        fmtr(URL(f"{scheme}://othercluster/other-project/%2525%3f%23"))
        == f"{scheme}://othercluster/other-project/%2525%3F%23"
    )


@pytest.mark.parametrize("scheme", ("storage", "image"))
def test_uri_formatter_special_chars_with_org(scheme: str) -> None:
    fmtr = uri_formatter(
        project_name="test-project", cluster_name="cluster", org_name="org"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/org/test-project/путь/к/файлу"))
        == f"{scheme}:%D0%BF%D1%83%D1%82%D1%8C/%D0%BA/%D1%84%D0%B0%D0%B9%D0%BB%D1%83"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/org/other-project/путь/к/файлу"))
        == f"{scheme}:/other-project/"
        "%D0%BF%D1%83%D1%82%D1%8C/%D0%BA/%D1%84%D0%B0%D0%B9%D0%BB%D1%83"
    )
    assert (
        fmtr(URL(f"{scheme}://othercluster/org/test-project/путь/к/файлу"))
        == f"{scheme}://othercluster/org/test-project/"
        "%D0%BF%D1%83%D1%82%D1%8C/%D0%BA/%D1%84%D0%B0%D0%B9%D0%BB%D1%83"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/org/test-project/%2525%3f%23"))
        == f"{scheme}:%2525%3F%23"
    )
    assert (
        fmtr(URL(f"{scheme}://cluster/org/other-project/%2525%3f%23"))
        == f"{scheme}:/other-project/%2525%3F%23"
    )
    assert (
        fmtr(URL(f"{scheme}://othercluster/org/test-project/%2525%3f%23"))
        == f"{scheme}://othercluster/org/test-project/%2525%3F%23"
    )
