import os
import sys
from typing import Any, AsyncIterator, Callable, Dict, Iterator
from unittest import mock

import pytest
from aiodocker.exceptions import DockerError
from aiohttp import web
from aiohttp.hdrs import LINK
from yarl import URL

from apolo_sdk import (
    AuthorizationError,
    Client,
    LocalImage,
    RemoteImage,
    Tag,
    TagOption,
)
from apolo_sdk._parsing_utils import _get_url_authority, _ImageNameParser

from tests import _TestServerFactory

_MakeClient = Callable[..., Client]


@pytest.fixture()
def patch_docker_host() -> Iterator[None]:
    with mock.patch.dict(os.environ, values={"DOCKER_HOST": "http://localhost:45678"}):
        yield


class TestImageParser:
    parser = _ImageNameParser(
        default_cluster="default",
        default_org="NO_ORG",
        default_project="test-project",
        registry_urls={
            "default": URL("https://reg.neu.ro"),
            "another": URL("https://example.org"),
        },
    )
    parser_with_org = _ImageNameParser(
        default_cluster="default",
        default_org="test-org",
        default_project="test-project",
        registry_urls={
            "default": URL("https://reg.neu.ro"),
            "another": URL("https://example.org"),
        },
    )

    @pytest.mark.parametrize(
        "image",
        [
            "image://default/project/ubuntu:v10.04",
            "image://another/project/ubuntu:v10.04",
            "image:ubuntu:v10.04",
            "image:///ubuntu:v10.04",
            "image:ubuntu:v10.04",
            "ubuntu:v10.04",
        ],
    )
    def test_has_tag_ok(self, image: str) -> None:
        assert self.parser.has_tag(image)

    def test_has_tag_no_tag(self) -> None:
        image = "ubuntu"
        assert not self.parser.has_tag(image)

    def test_has_tag_no_tag_with_slash(self) -> None:
        image = "library/ubuntu"
        assert not self.parser.has_tag(image)

    def test_has_tag_empty_tag(self) -> None:
        image = "ubuntu:"
        with pytest.raises(ValueError, match="empty tag"):
            self.parser.has_tag(image)

    def test_has_tag_empty_tag_with_slash(self) -> None:
        image = "library/ubuntu:"
        with pytest.raises(ValueError, match="empty tag"):
            self.parser.has_tag(image)

    def test_has_tag_empty_image_name(self) -> None:
        image = ":latest"
        with pytest.raises(ValueError, match="empty name"):
            self.parser.has_tag(image)

    def test_has_tag_too_many_tags(self) -> None:
        image = "ubuntu:v10.04:latest"
        with pytest.raises(ValueError, match="too many tags"):
            self.parser.has_tag(image)

    def test_has_tag_lstrip(self) -> None:
        image = "image:game:latest"
        assert self.parser.has_tag(image)
        image = "image:game:mega"
        assert self.parser.has_tag(image)
        image = "image:game:v2.0:latest"
        with pytest.raises(ValueError, match="too many tags"):
            assert self.parser.has_tag(image)

    @pytest.mark.parametrize(
        "registry_url",
        ["http://reg.neu.ro", "https://reg.neu.ro", "https://reg.neu.ro/bla/bla"],
    )
    def test_get_registry_hostname(self, registry_url: str) -> None:
        parser = _ImageNameParser(
            default_cluster="test-cluster",
            default_org="NO_ORG",
            default_project="test-project",
            registry_urls={"test-cluster": URL(registry_url)},
        )
        assert parser._registries == {"test-cluster": "reg.neu.ro"}

    @pytest.mark.parametrize(
        "registry_url", ["http://reg.neu.ro:5000", "http://reg.neu.ro:5000/bla/bla"]
    )
    def test_get_registry_hostname_with_port(self, registry_url: str) -> None:
        parser = _ImageNameParser(
            default_cluster="test-cluster",
            default_org="NO_ORG",
            default_project="test-project",
            registry_urls={"test-cluster": URL(registry_url)},
        )
        assert parser._registries == {"test-cluster": "reg.neu.ro:5000"}

    @pytest.mark.parametrize(
        "registry_url",
        ["", "reg.neu.ro", "reg.neu.ro:5000", "https://", "https:///bla/bla"],
    )
    def test_get_registry_hostname__bad_url_empty_hostname(
        self, registry_url: str
    ) -> None:
        with pytest.raises(ValueError, match="Empty hostname in registry URL"):
            _ImageNameParser(
                default_cluster="test-cluster",
                default_org="NO_ORG",
                default_project="test-project",
                registry_urls={"test-cluster": URL(registry_url)},
            )

    def test_split_image_name_no_tag(self) -> None:
        splitted = self.parser._split_image_name("ubuntu", "latest")
        assert splitted == ("ubuntu", "latest")

    def test_split_image_name_with_tag(self) -> None:
        splitted = self.parser._split_image_name("ubuntu:v10.04", "latest")
        assert splitted == ("ubuntu", "v10.04")

    def test_split_image_name_empty_tag(self) -> None:
        with pytest.raises(ValueError, match="empty tag"):
            self.parser._split_image_name("ubuntu:", "latest")

    def test_split_image_name_two_tags(self) -> None:
        with pytest.raises(ValueError, match="too many tags"):
            self.parser._split_image_name("ubuntu:v10.04:LTS", "latest")

    def test_split_image_name_with_registry_port_no_tag(self) -> None:
        splitted = self.parser._split_image_name("localhost:5000/ubuntu", "latest")
        assert splitted == ("localhost:5000/ubuntu", "latest")

    def test_split_image_name_with_registry_port_with_tag(self) -> None:
        splitted = self.parser._split_image_name(
            "localhost:5000/ubuntu:v10.04", "latest"
        )
        assert splitted == ("localhost:5000/ubuntu", "v10.04")

    def test_split_image_name_with_registry_port_two_tags(self) -> None:
        with pytest.raises(ValueError, match="too many tags"):
            self.parser._split_image_name("localhost:5000/ubuntu:v10.04:LTS", "latest")

    def test_split_image_name_with_registry_port_empty_tag(self) -> None:
        with pytest.raises(ValueError, match="empty tag"):
            self.parser._split_image_name("localhost:5000/ubuntu:", "latest")

    def test_split_image_name_with_registry_port_slash_in_tag(self) -> None:
        with pytest.raises(ValueError, match="invalid tag"):
            self.parser._split_image_name("localhost:5000/ubuntu:v10/04", "latest")

    # public method: parse_local

    @pytest.mark.parametrize(
        "url",
        [
            "image://",
            "image:///",
            "image://default/project",
            "image://default/project/",
        ],
    )
    def test_parse_as_apolo_image__no_image_name(self, url: str) -> None:
        with pytest.raises(ValueError, match="no image name specified"):
            self.parser.parse_as_platform_image(url)

    def test_parse_as_local_image_empty_fail(self) -> None:
        image = ""
        with pytest.raises(ValueError, match="empty image name"):
            self.parser.parse_as_local_image(image)

    def test_parse_as_local_image_dash_fail(self) -> None:
        image = "-zxc"
        with pytest.raises(ValueError, match="image cannot start with dash"):
            self.parser.parse_as_local_image(image)

    def test_parse_as_local_image_with_image_scheme_fail(self) -> None:
        image = "image://default/ubuntu"
        with pytest.raises(
            ValueError, match="scheme 'image://' is not allowed for local images"
        ):
            self.parser.parse_as_local_image(image)

    def test_parse_as_local_image_with_other_scheme_fail(self) -> None:
        image = "http://ubuntu"
        with pytest.raises(ValueError, match="invalid image name"):
            self.parser.parse_as_local_image(image)

    def test_parse_as_local_image_no_tag(self) -> None:
        image = "ubuntu"
        parsed = self.parser.parse_as_local_image(image)
        assert parsed == LocalImage(name="ubuntu", tag="latest")

    def test_parse_as_local_image_with_tag(self) -> None:
        image = "ubuntu:v10.04"
        parsed = self.parser.parse_as_local_image(image)
        assert parsed == LocalImage(name="ubuntu", tag="v10.04")
        assert self.parser.parse_as_local_image(str(parsed)) == parsed

    def test_parse_as_local_image_special_chars(self) -> None:
        image = "image#%2d?ß:tag#%2d?ß"
        with pytest.raises(ValueError):
            self.parser.parse_as_local_image(image)

    def test_parse_as_local_image_2_tag_fail(self) -> None:
        image = "ubuntu:v10.04:LTS"
        with pytest.raises(ValueError, match="too many tags"):
            self.parser.parse_as_local_image(image)

    # public method: parse_remote

    @pytest.mark.parametrize(
        "url",
        [
            "image://default/project/ubuntu:v10.04?key=value",
            "image://default/project/ubuntu?key=value",
            "image:///ubuntu?key=value",
            "image:ubuntu?key=value",
            "image:5000?key=value",
            "image://default/project/ubuntu:v10.04?",
        ],
    )
    def test_parse_as_apolo_image__with_query__fail(self, url: str) -> None:
        with pytest.raises(ValueError, match="Query part is not allowed in image URI"):
            self.parser.parse_as_platform_image(url)

    @pytest.mark.parametrize(
        "url",
        [
            "image://default/project/ubuntu:v10.04#fragment",
            "image://default/project/ubuntu#fragment",
            "image:///ubuntu#fragment",
            "image:ubuntu#fragment",
            "image:5000#fragment",
            "image://default/project/ubuntu:v10.04#",
        ],
    )
    def test_parse_as_apolo_image__with_fragment__fail(self, url: str) -> None:
        with pytest.raises(
            ValueError, match="Fragment part is not allowed in image URI"
        ):
            self.parser.parse_as_platform_image(url)

    def test_parse_as_apolo_image__with_user__fail(self) -> None:
        url = "image://user@default/project/ubuntu"
        with pytest.raises(ValueError, match="User is not allowed in image URI"):
            self.parser.parse_as_platform_image(url)

    def test_parse_as_apolo_image__with_password__fail(self) -> None:
        url = "image://:password@default/project/ubuntu"
        with pytest.raises(ValueError, match="Password is not allowed in image URI"):
            self.parser.parse_as_platform_image(url)

    def test_parse_as_apolo_image__with_empty_password__fail(self) -> None:
        url = "image://:@default/project/ubuntu"
        with pytest.raises(ValueError, match="Password is not allowed in image URI"):
            self.parser.parse_as_platform_image(url)

    def test_parse_as_apolo_image__with_port__fail(self) -> None:
        url = "image://default:443/project/ubuntu"
        with pytest.raises(ValueError, match="Port is not allowed in image URI"):
            self.parser.parse_as_platform_image(url)

    def test_parse_as_apolo_image_empty__fail(self) -> None:
        image = ""
        with pytest.raises(ValueError, match="empty image name"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_dash__fail(self) -> None:
        image = "-zxc"
        with pytest.raises(ValueError, match="image cannot start with dash"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_no_scheme_fail(self) -> None:
        image = "ubuntu"
        with pytest.raises(
            ValueError, match="scheme 'image:' is required for remote images"
        ):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_invalid_scheme_1_fail(self) -> None:
        image = "ubuntu:latest"
        with pytest.raises(
            ValueError, match="scheme 'image:' is required for remote images"
        ):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_invalid_scheme_2_fail(self) -> None:
        image = "http://ubuntu"
        with pytest.raises(
            ValueError, match="scheme 'image:' is required for remote images"
        ):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_default_org_no_org(self) -> None:
        image = "image://another/project/ubuntu:v10.04"
        parsed = self.parser_with_org.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="another",
            registry="example.org",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_default_org_no_cluster_no_org(self) -> None:
        image = "image:/project/ubuntu:v10.04"
        parsed = self.parser_with_org.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="test-org",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_default_org_no_cluster_no_project(self) -> None:
        image = "image:ubuntu:v10.04"
        parsed = self.parser_with_org.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="test-org",
            project_name="test-project",
        )

    def test_parse_as_apolo_image_with_default_org_same_org(self) -> None:
        image = "image://another/test-org/project/ubuntu:v10.04"
        parsed = self.parser_with_org.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="another",
            registry="example.org",
            org_name="test-org",
            project_name="project",
        )

    # XXX: Ambigious URI
    def test_parse_as_apolo_image_with_default_org_other_org(self) -> None:
        image = "image://another/org/project/ubuntu:v10.04"
        parsed = self.parser_with_org.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="project/ubuntu",
            tag="v10.04",
            cluster_name="another",
            registry="example.org",
            org_name="NO_ORG",
            project_name="org",
        )

    # XXX: Ambigious URI
    def test_parse_as_apolo_image_without_default_org_with_org(self) -> None:
        image = "image://another/test-org/project/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="project/ubuntu",
            tag="v10.04",
            cluster_name="another",
            registry="example.org",
            org_name="NO_ORG",
            project_name="test-org",
        )

    def test_parse_as_apolo_image_with_scheme_with_cluster_with_project_with_tag(
        self,
    ) -> None:
        image = "image://another/project/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="another",
            registry="example.org",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_with_cluster_with_project_with_tag_2(
        self,
    ) -> None:
        image = "image://another/project/library/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="v10.04",
            cluster_name="another",
            registry="example.org",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_with_cluster_with_project_no_tag(
        self,
    ) -> None:
        image = "image://another/project/ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="latest",
            cluster_name="another",
            registry="example.org",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_with_cluster_with_project_no_tag_2(
        self,
    ) -> None:
        image = "image://another/project/library/ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="latest",
            cluster_name="another",
            registry="example.org",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_unknown_cluster(self) -> None:
        image = "image://unknown-cluster/project/ubuntu"
        with pytest.raises(
            RuntimeError,
            match="Cluster unknown-cluster doesn't exist "
            "in a list of available clusters",
        ):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_scheme_no_slash_no_cluster_no_project_no_tag(
        self,
    ) -> None:
        image = "image:ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="test-project",
        )

    def test_parse_as_apolo_image_with_scheme_no_slash_no_cluster_no_project_no_tag_2(
        self,
    ) -> None:
        image = "image:library/ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="test-project",
        )

    def test_parse_as_apolo_image_with_scheme_no_slash_no_cluster_no_project_with_tag(
        self,
    ) -> None:
        image = "image:ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="test-project",
        )

    def test_parse_as_apolo_image_with_scheme_no_slash_no_cluster_no_project_with_tag_2(
        self,
    ) -> None:
        image = "image:library/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="test-project",
        )

    def test_parse_as_apolo_image_with_scheme_1_slash_no_cluster_no_name_no_tag(
        self,
    ) -> None:
        image = "image:/ubuntu"
        with pytest.raises(ValueError, match="no image name specified"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_scheme_1_slash_no_cluster_no_tag(self) -> None:
        image = "image:/project/ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_1_slash_no_cluster_no_tag_2(self) -> None:
        image = "image:/project/library/ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_1_slash_no_cluster_no_name_with_tag(
        self,
    ) -> None:
        image = "image:/ubuntu:v10.04"
        with pytest.raises(ValueError, match="no image name specified"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_scheme_1_slash_no_cluster_with_tag(self) -> None:
        image = "image:/project/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_1_slash_no_cluster_with_tag_2(
        self,
    ) -> None:
        image = "image:/project/library/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_2_slash_cluster_proj_no_name_no_tag_fail(
        self,
    ) -> None:
        image = "image://another/ubuntu"
        with pytest.raises(ValueError, match="no image name specified"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_scheme_2_slash_cluster_no_project_with_tag_fail(
        self,
    ) -> None:
        image = "image://ubuntu:v10.04"
        with pytest.raises(ValueError, match="port can't be converted to integer"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_scheme_3_slash_no_cluster_no_name_no_tag(
        self,
    ) -> None:
        image = "image:///ubuntu"
        with pytest.raises(ValueError, match="no image name specified"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_scheme_3_slash_no_cluster_no_tag(self) -> None:
        image = "image:///project/ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_3_slash_no_cluster_no_tag_2(self) -> None:
        image = "image:///project/library/ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_3_slash_no_cluster_no_name_with_tag(
        self,
    ) -> None:
        image = "image:///ubuntu:v10.04"
        with pytest.raises(ValueError, match="no image name specified"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_scheme_3_slash_no_cluster_with_tag(self) -> None:
        image = "image:///project/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_3_slash_no_cluster_with_tag_2(
        self,
    ) -> None:
        image = "image:///project/library/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_4_slash_no_cluster_no_name_with_tag(
        self,
    ) -> None:
        image = "image:////ubuntu:v10.04"
        with pytest.raises(ValueError, match="no image name specified"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_scheme_4_slash_no_cluster_with_tag(self) -> None:
        image = "image:////project/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_4_slash_no_cluster_with_tag_2(
        self,
    ) -> None:
        image = "image:////project/library/ubuntu:v10.04"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="v10.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_4_slash_no_cluster_no_name_no_tag(
        self,
    ) -> None:
        image = "image:////ubuntu"
        with pytest.raises(ValueError, match="no image name specified"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_scheme_4_slash_no_cluster_no_tag(self) -> None:
        image = "image:////project/ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_4_slash_no_cluster_no_tag_2(self) -> None:
        image = "image:////project/library/ubuntu"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image_with_scheme_special_chars(self) -> None:
        image = (
            "image://another/project/ubuntu%23%252d%3F%C3%9F:v10.04%23%252d%3F%C3%9F"
        )
        with pytest.raises(ValueError, match="invalid image name"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_no_scheme_no_slash_no_tag_fail(self) -> None:
        image = "ubuntu"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_no_scheme_no_slash_with_tag_fail(self) -> None:
        image = "ubuntu:v10.04"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_no_scheme_1_slash_no_tag_fail(self) -> None:
        image = "library/ubuntu"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_no_scheme_1_slash_with_tag_fail(self) -> None:
        image = "library/ubuntu:v10.04"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_no_scheme_2_slash_no_tag_fail(self) -> None:
        image = "docker.io/library/ubuntu"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_no_scheme_2_slash_with_tag_fail(self) -> None:
        image = "docker.io/library/ubuntu:v10.04"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_no_scheme_3_slash_no_tag_fail(self) -> None:
        image = "something/docker.io/library/ubuntu"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_with_registry_prefix(self) -> None:
        image = self.parser.parse_as_platform_image("reg.neu.ro/project/image:tag")
        assert str(image) == "image://default/NO_ORG/project/image:tag"

    def test_parse_as_apolo_image_with_registry_prefix_special_chars(self) -> None:
        with pytest.raises(ValueError, match="invalid image name"):
            self.parser.parse_as_platform_image(
                "reg.neu.ro/project/image%23%252d%3F%C3%9F:tag%23%252d%3F%C3%9F"
            )

    def test_parse_as_apolo_image_no_scheme_3_slash_with_tag_fail(self) -> None:
        image = "something/docker.io/library/ubuntu:v10.04"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            self.parser.parse_as_platform_image(image)

    def test_parse_as_apolo_image_allow_tag_false_with_scheme_no_tag(self) -> None:
        image = "image:ubuntu"
        parsed = self.parser.parse_as_platform_image(image, tag_option=TagOption.DENY)
        assert parsed == RemoteImage.new_platform_image(
            name="ubuntu",
            tag=None,
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="test-project",
        )

    def test_parse_as_apolo_image_allow_tag_false_no_scheme_no_tag(self) -> None:
        image = "ubuntu"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            self.parser.parse_as_platform_image(image, tag_option=TagOption.DENY)

    def test_parse_as_apolo_image_allow_tag_false_no_scheme_with_tag(self) -> None:
        image = "ubuntu:latest"
        with pytest.raises(ValueError, match="tag is not allowed"):
            self.parser.parse_as_platform_image(image, tag_option=TagOption.DENY)

    def test_parse_as_apolo_image_allow_tag_false_with_scheme_lstrip(self) -> None:
        image = "image:game:latest"
        with pytest.raises(ValueError, match="tag is not allowed"):
            self.parser.parse_as_platform_image(image, tag_option=TagOption.DENY)
        image = "image:game:mega"
        with pytest.raises(ValueError, match="tag is not allowed"):
            self.parser.parse_as_platform_image(image, tag_option=TagOption.DENY)
        image = "image:game:v2.0:latest"
        with pytest.raises(ValueError, match="too many tags"):
            self.parser.parse_as_platform_image(image, tag_option=TagOption.DENY)

    def test_convert_to_local_image(self) -> None:
        platform_image = RemoteImage.new_platform_image(
            name="ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.com",
            org_name="NO_ORG",
            project_name="project",
        )
        local_image = self.parser.convert_to_local_image(platform_image)
        assert local_image == LocalImage(name="ubuntu", tag="latest")

    def test_convert_to_apolo_image(self) -> None:
        local_image = LocalImage(name="ubuntu", tag="latest")
        platform_image = self.parser.convert_to_platform_image(local_image)
        assert platform_image == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="test-project",
        )

    def test_convert_to_apolo_image_with_default_org(self) -> None:
        local_image = LocalImage(name="ubuntu", tag="latest")
        platform_image = self.parser_with_org.convert_to_platform_image(local_image)
        assert platform_image == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="test-org",
            project_name="test-project",
        )

    def test_convert_to_apolo_image__platform_registry(self) -> None:
        local_image = LocalImage(name="reg.neu.ro/project/ubuntu", tag="v20.04")
        platform_image = self.parser.convert_to_platform_image(local_image)
        assert platform_image == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v20.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_convert_to_apolo_image__platform_registry__no_project(self) -> None:
        local_image = LocalImage(name="reg.neu.ro/ubuntu", tag="v20.04")
        platform_image = self.parser.convert_to_platform_image(local_image)
        assert platform_image == RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v20.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="test-project",
        )

    def test_convert_to_apolo_image__platform_registry__no_path(self) -> None:
        local_image = LocalImage(name="reg.neu.ro/", tag="v20.04")
        platform_image = self.parser.convert_to_platform_image(local_image)
        assert platform_image == RemoteImage.new_platform_image(
            name="reg.neu.ro/",
            tag="v20.04",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="test-project",
        )

    # corner case 'image:latest'

    def test_parse_as_apolo_image__ambiguous_case__fail(self) -> None:
        url = "image:latest"
        with pytest.raises(ValueError, match="ambiguous value"):
            self.parser.parse_as_platform_image(url)

    def test_parse_as_local_image__ambiguous_case__fail(self) -> None:
        url = "image:latest"
        with pytest.raises(ValueError, match="ambiguous value"):
            self.parser.parse_as_local_image(url)

    # other corner cases

    def test_parse_as_apolo_image__numeric_name(self) -> None:
        image = "image:5000"
        parsed = self.parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="5000",
            tag="latest",
            cluster_name="default",
            registry="reg.neu.ro",
            org_name="NO_ORG",
            project_name="test-project",
        )

    def test_parse_as_local_image__platform_registry(self) -> None:
        image = "reg.neu.ro/project/ubuntu:v10.04"
        parsed = self.parser.parse_as_local_image(image)
        assert parsed == LocalImage(name="reg.neu.ro/project/ubuntu", tag="v10.04")

    def test_parse_as_local_image__registry_has_port__platform_registry(self) -> None:
        my_parser = _ImageNameParser(
            default_cluster="test-cluster",
            default_org="NO_ORG",
            default_project="test-project",
            registry_urls={"test-cluster": URL("http://localhost:5000")},
        )
        image = "localhost:5000/project/ubuntu:v10.04"
        parsed = my_parser.parse_as_local_image(image)
        assert parsed == LocalImage(name="localhost:5000/project/ubuntu", tag="v10.04")

    def test_parse_as_apolo_image__registry_has_port__platform_image(self) -> None:
        my_parser = _ImageNameParser(
            default_cluster="test-cluster",
            default_org="NO_ORG",
            default_project="test-project",
            registry_urls={"test-cluster": URL("http://localhost:5000")},
        )
        image = "image://test-cluster/project/library/ubuntu:v10.04"
        parsed = my_parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="v10.04",
            cluster_name="test-cluster",
            registry="localhost:5000",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image__registry_has_port__image_in_good_repo(self) -> None:
        my_parser = _ImageNameParser(
            default_cluster="test-cluster",
            default_org="NO_ORG",
            default_project="test-project",
            registry_urls={"test-cluster": URL("http://localhost:5000")},
        )
        image = "localhost:5000/project/library/ubuntu:v10.04"
        parsed = my_parser.parse_as_platform_image(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="v10.04",
            cluster_name="test-cluster",
            registry="localhost:5000",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_as_apolo_image__registry_has_port__image_in_bad_repo(self) -> None:
        my_parser = _ImageNameParser(
            default_cluster="test-cluster",
            default_org="NO_ORG",
            default_project="test-project",
            registry_urls={"test-cluster": URL("http://localhost:5000")},
        )
        image = "localhost:9999/project/library/ubuntu:v10.04"
        with pytest.raises(ValueError, match="scheme 'image:' is required"):
            my_parser.parse_as_platform_image(image)

    def test_parse_remote__registry_has_port__platform_image(self) -> None:
        my_parser = _ImageNameParser(
            default_cluster="test-cluster",
            default_org="NO_ORG",
            default_project="test-project",
            registry_urls={"test-cluster": URL("http://localhost:5000")},
        )
        image = "image://test-cluster/project/library/ubuntu:v10.04"
        parsed = my_parser.parse_remote(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="v10.04",
            cluster_name="test-cluster",
            registry="localhost:5000",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_remote__registry_has_port__image_in_good_repo(self) -> None:
        my_parser = _ImageNameParser(
            default_cluster="test-cluster",
            default_org="NO_ORG",
            default_project="test-project",
            registry_urls={"test-cluster": URL("http://localhost:5000")},
        )
        image = "localhost:5000/project/library/ubuntu:v10.04"
        parsed = my_parser.parse_remote(image)
        assert parsed == RemoteImage.new_platform_image(
            name="library/ubuntu",
            tag="v10.04",
            cluster_name="test-cluster",
            registry="localhost:5000",
            org_name="NO_ORG",
            project_name="project",
        )

    def test_parse_remote__registry_has_port__image_in_other_repo(self) -> None:
        my_parser = _ImageNameParser(
            default_cluster="test-cluster",
            default_org="NO_ORG",
            default_project="test-project",
            registry_urls={"test-cluster": URL("http://localhost:5000")},
        )
        image = "example.com:9999/project/library/ubuntu:v10.04"
        parsed = my_parser.parse_remote(image)
        # NOTE: "owner" is parsed only for images in neuro registry
        assert parsed == RemoteImage.new_external_image(
            name="project/library/ubuntu",
            tag="v10.04",
            registry="example.com:9999",
        )


class TestRemoteImage:
    def test_as_str_in_neuro_registry_tag_none(self) -> None:
        image = RemoteImage.new_platform_image(
            name="ubuntu",
            tag=None,
            cluster_name="test-cluster",
            org_name=None,
            registry="registry.io",
            project_name="test-project",
        )
        assert str(image) == "image://test-cluster/test-project/ubuntu"
        assert image.as_docker_url() == "registry.io/test-project/ubuntu"

    def test_as_str_in_neuro_registry_tag_yes(self) -> None:
        image = RemoteImage.new_platform_image(
            name="ubuntu",
            tag="v10.04",
            cluster_name="test-cluster",
            registry="registry.io",
            org_name=None,
            project_name="test-project",
        )
        assert str(image) == "image://test-cluster/test-project/ubuntu:v10.04"
        assert image.as_docker_url() == "registry.io/test-project/ubuntu:v10.04"

    def test_as_str_in_neuro_registry_tag_special_chars(self) -> None:
        image = RemoteImage.new_platform_image(
            name="image#%2d?ß",
            tag="tag#%2d?ß",
            cluster_name="test-cluster",
            registry="registry.io",
            org_name=None,
            project_name="test-project",
        )
        assert str(image) == (
            "image://test-cluster/test-project/"
            "image%23%252d%3F%C3%9F:tag%23%252d%3F%C3%9F"
        )
        assert image.as_docker_url() == "registry.io/test-project/image#%2d?ß:tag#%2d?ß"

    def test_as_str_not_in_neuro_registry_tag_none(self) -> None:
        image = RemoteImage.new_external_image(name="ubuntu")
        assert str(image) == "ubuntu"
        assert image.as_docker_url() == "ubuntu"

    def test_as_str_not_in_neuro_registry_tag_yes(self) -> None:
        image = RemoteImage.new_external_image(name="ubuntu", tag="v10.04")
        assert str(image) == "ubuntu:v10.04"
        assert image.as_docker_url() == "ubuntu:v10.04"

    def test_as_docker_url_in_neuro_registry(self) -> None:
        image = RemoteImage(
            name="ubuntu",
            tag="v10.04",
            cluster_name="test-cluster",
            registry="registry.io",
            project_name="test-project",
        )
        assert image.as_docker_url() == "registry.io/test-project/ubuntu:v10.04"

    def test_as_docker_url_not_in_neuro_registry(self) -> None:
        image = RemoteImage(name="ubuntu", tag="v10.04", registry=None)
        assert image.as_docker_url() == "ubuntu:v10.04"


@pytest.mark.usefixtures("patch_docker_host")
class TestImages:
    parser = _ImageNameParser(
        default_cluster="default",
        default_org="NO_ORG",
        default_project="test-project",
        registry_urls={"default": URL("https://registry-api.dev.apolo.us")},
    )

    @mock.patch(
        "aiodocker.Docker.__init__",
        side_effect=ValueError(
            "text Either DOCKER_HOST or local sockets are not available text"
        ),
    )
    async def test_unavailable_docker(
        self, patched_init: Any, make_client: _MakeClient
    ) -> None:
        image = self.parser.parse_as_platform_image(
            "image://default/project/image:bananas"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            with pytest.raises(DockerError, match=r"Docker engine is not available.+"):
                await client.images.pull(image, local_image)

    @mock.patch(
        "aiodocker.Docker.__init__", side_effect=ValueError("something went wrong")
    )
    async def test_unknown_docker_error(
        self, patched_init: Any, make_client: _MakeClient
    ) -> None:
        image = self.parser.parse_as_platform_image(
            "image://default/project/image:bananas"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            with pytest.raises(ValueError, match=r"something went wrong"):
                await client.images.pull(image, local_image)

    @mock.patch("aiodocker.images.DockerImages.tag")
    async def test_push_non_existent_image(
        self, patched_tag: Any, make_client: _MakeClient
    ) -> None:
        patched_tag.side_effect = DockerError(404, {"message": "Mocked error"})
        image = self.parser.parse_as_platform_image(
            "image://default/project/image:bananas-no-more"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            with pytest.raises(ValueError, match=r"not found"):
                await client.images.push(local_image, image)

    @mock.patch("aiodocker.images.DockerImages.tag")
    @mock.patch("aiodocker.images.DockerImages.push")
    async def test_push_image_to_foreign_repo(
        self, patched_push: Any, patched_tag: Any, make_client: _MakeClient
    ) -> None:
        patched_tag.return_value = True
        patched_push.side_effect = DockerError(403, {"message": "Mocked error"})
        image = self.parser.parse_as_platform_image(
            "image://default/project/image:bananas-no-more"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            with pytest.raises(AuthorizationError):
                await client.images.push(local_image, image)

    @mock.patch("aiodocker.images.DockerImages.tag")
    @mock.patch("aiodocker.images.DockerImages.push")
    async def test_push_image_with_docker_api_error(
        self, patched_push: Any, patched_tag: Any, make_client: _MakeClient
    ) -> None:
        async def error_generator() -> AsyncIterator[Dict[str, Any]]:
            yield {"error": True, "errorDetail": {"message": "Mocked message"}}

        patched_tag.return_value = True
        patched_push.return_value = error_generator()
        image = self.parser.parse_as_platform_image(
            "image://default/project/image:bananas-wrong-food"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            with pytest.raises(DockerError) as exc_info:
                await client.images.push(local_image, image)
        assert exc_info.value.status == 900
        assert exc_info.value.message == "Mocked message"

    @mock.patch("aiodocker.images.DockerImages.tag")
    @mock.patch("aiodocker.images.DockerImages.push")
    async def test_success_push_image(
        self, patched_push: Any, patched_tag: Any, make_client: _MakeClient
    ) -> None:
        async def message_generator() -> AsyncIterator[Dict[str, Any]]:
            yield {}

        patched_tag.return_value = True
        patched_push.return_value = message_generator()
        image = self.parser.parse_as_platform_image(
            "image://default/project/image:bananas-is-here"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            result = await client.images.push(local_image, image)
        assert result == image

    @mock.patch("aiodocker.images.DockerImages.tag")
    @mock.patch("aiodocker.images.DockerImages.push")
    async def test_success_push_image_no_target(
        self, patched_push: Any, patched_tag: Any, make_client: _MakeClient
    ) -> None:
        async def message_generator() -> AsyncIterator[Dict[str, Any]]:
            yield {}

        patched_tag.return_value = True
        patched_push.return_value = message_generator()
        image = self.parser.parse_as_platform_image(
            "image://default/NO_ORG/test-project/bananas:latest"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            result = await client.images.push(local_image)
        assert result == image

    @mock.patch("aiodocker.images.DockerImages.pull")
    async def test_pull_non_existent_image(
        self, patched_pull: Any, make_client: _MakeClient
    ) -> None:
        patched_pull.side_effect = DockerError(404, {"message": "Mocked error"})
        async with make_client("https://api.localhost.localdomain") as client:
            image = self.parser.parse_as_platform_image(
                "image://default/project/image:no-bananas-here"
            )
            local_image = self.parser.parse_as_local_image("bananas:latest")
            with pytest.raises(ValueError, match=r"not found"):
                await client.images.pull(image, local_image)

    @mock.patch("aiodocker.images.DockerImages.pull")
    async def test_pull_image_from_foreign_repo(
        self, patched_pull: Any, make_client: _MakeClient
    ) -> None:
        patched_pull.side_effect = DockerError(403, {"message": "Mocked error"})
        image = self.parser.parse_as_platform_image(
            "image://default/project/image:not-your-bananas"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            with pytest.raises(AuthorizationError):
                await client.images.pull(image, local_image)

    @mock.patch("aiodocker.images.DockerImages.pull")
    async def test_pull_image_with_docker_api_error(
        self, patched_pull: Any, make_client: Any
    ) -> None:
        async def error_generator() -> AsyncIterator[Dict[str, Any]]:
            yield {"error": True, "errorDetail": {"message": "Mocked message"}}

        patched_pull.return_value = error_generator()
        image = self.parser.parse_as_platform_image(
            "image://default/project/image:nuts-here"
        )
        async with make_client("https://api.localhost.localdomain") as client:
            with pytest.raises(DockerError) as exc_info:
                await client.images.pull(image, image)
        assert exc_info.value.status == 900
        assert exc_info.value.message == "Mocked message"

    @mock.patch("aiodocker.images.DockerImages.tag")
    @mock.patch("aiodocker.images.DockerImages.pull")
    async def test_success_pull_image(
        self, patched_pull: Any, patched_tag: Any, make_client: _MakeClient
    ) -> None:
        async def message_generator() -> AsyncIterator[Dict[str, Any]]:
            yield {}

        patched_tag.return_value = True
        patched_pull.return_value = message_generator()
        image = self.parser.parse_as_platform_image(
            "image://default/project/image:bananas"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            result = await client.images.pull(image, local_image)
        assert result == local_image

    @mock.patch("aiodocker.images.DockerImages.tag")
    @mock.patch("aiodocker.images.DockerImages.pull")
    async def test_success_pull_image_no_target(
        self, patched_pull: Any, patched_tag: Any, make_client: _MakeClient
    ) -> None:
        async def message_generator() -> AsyncIterator[Dict[str, Any]]:
            yield {}

        patched_tag.return_value = True
        patched_pull.return_value = message_generator()
        image = self.parser.parse_as_platform_image(
            "image://default/project/bananas:latest"
        )
        local_image = self.parser.parse_as_local_image("bananas:latest")
        async with make_client("https://api.localhost.localdomain") as client:
            result = await client.images.pull(image)
        assert result == local_image


class TestRegistry:
    @pytest.mark.skipif(
        sys.platform == "win32", reason="aiodocker doesn't support Windows pipes yet"
    )
    async def test_ls_repositories(
        self, aiohttp_server: _TestServerFactory, make_client: _MakeClient
    ) -> None:
        JSON = {"repositories": ["project1/alpine", "project2/bananas"]}

        async def handler(request: web.Request) -> web.Response:
            assert "n" in request.query
            assert "last" not in request.query
            return web.json_response(JSON)

        app = web.Application()
        app.router.add_get("/v2/_catalog", handler)

        srv = await aiohttp_server(app)
        url = "http://platform"
        registry_url = srv.make_url("/v2/")

        async with make_client(url, registry_url=registry_url) as client:
            ret = await client.images.list()

        registry = _get_url_authority(registry_url)
        assert registry is not None
        assert set(ret) == {
            RemoteImage.new_platform_image(
                "alpine",
                tag=None,
                cluster_name="default",
                registry=registry,
                org_name="NO_ORG",
                project_name="project1",
            ),
            RemoteImage.new_platform_image(
                "bananas",
                tag=None,
                cluster_name="default",
                registry=registry,
                org_name="NO_ORG",
                project_name="project2",
            ),
        }

    async def test_ls_repositories_chunked(
        self, aiohttp_server: _TestServerFactory, make_client: _MakeClient
    ) -> None:
        step = 0

        async def handler(request: web.Request) -> web.Response:
            nonlocal step
            step += 1
            headers: Dict[str, str]
            assert "n" in request.query
            if step == 1:
                assert "last" not in request.query
                payload = {"repositories": ["project1/alpine", "project2/bananas"]}
                headers = {LINK: f'<{catalog_url}?last=lsttkn>; rel="next"'}
                return web.json_response(payload, headers=headers)
            elif step == 2:
                assert request.query["last"] == "lsttkn"
                payload = {"repositories": ["project3/library/ubuntu"]}
                headers = {LINK: f'<{catalog_url}?last=lsttkn2>; rel="next"'}
                return web.json_response(payload, headers=headers)
            elif step == 3:
                assert request.query["last"] == "lsttkn2"
                payload = {"repositories": []}
                headers = {LINK: f'<{catalog_url}?last=lsttkn3>; rel="next"'}
                return web.json_response(payload, headers=headers)
            else:  # pragma: no cover
                assert False

        app = web.Application()
        app.router.add_get("/v2/_catalog", handler)

        srv = await aiohttp_server(app)
        url = "http://platform"
        registry_url = srv.make_url("/v2/")
        catalog_url = registry_url / "_catalog"

        registry = _get_url_authority(registry_url)
        assert registry is not None
        expected = {
            RemoteImage.new_platform_image(
                "alpine",
                tag=None,
                cluster_name="default",
                registry=registry,
                org_name="NO_ORG",
                project_name="project1",
            ),
            RemoteImage.new_platform_image(
                "library/ubuntu",
                tag=None,
                cluster_name="default",
                registry=registry,
                org_name="NO_ORG",
                project_name="project3",
            ),
            RemoteImage.new_platform_image(
                "bananas",
                tag=None,
                cluster_name="default",
                registry=registry,
                org_name="NO_ORG",
                project_name="project2",
            ),
        }

        async with make_client(url, registry_url=registry_url) as client:
            ret = await client.images.list()
        assert step == 3  # All steps are passed
        assert set(ret) == expected

    @pytest.mark.skipif(
        sys.platform == "win32", reason="aiodocker doesn't support Windows pipes yet"
    )
    async def test_ls_tags(
        self, aiohttp_server: _TestServerFactory, make_client: _MakeClient
    ) -> None:
        JSON = {"name": "test", "tags": ["alpha", "beta", "gamma"]}

        async def handler(request: web.Request) -> web.Response:
            assert "n" in request.query
            assert "last" not in request.query
            return web.json_response(JSON)

        app = web.Application()
        app.router.add_get("/v2/project/test/tags/list", handler)

        srv = await aiohttp_server(app)
        url = "http://platform"
        registry_url = srv.make_url("/v2/")

        async with make_client(url, registry_url=registry_url) as client:
            image = RemoteImage.new_platform_image(
                name="test",
                tag=None,
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            )
            ret = await client.images.tags(image)

        assert set(ret) == {
            RemoteImage.new_platform_image(
                "test",
                tag="alpha",
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            ),
            RemoteImage.new_platform_image(
                "test",
                tag="beta",
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            ),
            RemoteImage.new_platform_image(
                "test",
                tag="gamma",
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            ),
        }

    async def test_ls_tags_chunked(
        self, aiohttp_server: _TestServerFactory, make_client: _MakeClient
    ) -> None:
        step = 0

        async def handler(request: web.Request) -> web.Response:
            nonlocal step
            step += 1
            headers: Dict[str, str]
            assert "n" in request.query
            if step == 1:
                assert "last" not in request.query
                payload = {"name": "test", "tags": ["alpha", "beta"]}
                headers = {LINK: f'<{tags_list_url}?last=lsttkn>; rel="next"'}
                return web.json_response(payload, headers=headers)
            elif step == 2:
                assert request.query["last"] == "lsttkn"
                payload = {"name": "test", "tags": ["gamma"]}
                headers = {LINK: f'<{tags_list_url}?last=lsttkn2>; rel="next"'}
                return web.json_response(payload, headers=headers)
            elif step == 3:
                assert request.query["last"] == "lsttkn2"
                payload = {"name": "test", "tags": []}
                headers = {LINK: f'<{tags_list_url}?last=lsttkn3>; rel="next"'}
                return web.json_response(payload, headers=headers)
            else:  # pragma: no cover
                assert False

        app = web.Application()
        app.router.add_get("/v2/project/test/tags/list", handler)

        srv = await aiohttp_server(app)
        url = "http://platform"
        registry_url = srv.make_url("/v2/")
        tags_list_url = registry_url / "project/test/tags/list"

        async with make_client(url, registry_url=registry_url) as client:
            image = RemoteImage.new_platform_image(
                name="test",
                tag=None,
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            )
            ret = await client.images.tags(image)
        assert step == 3  # All steps are passed

        assert set(ret) == {
            RemoteImage.new_platform_image(
                "test",
                tag="alpha",
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            ),
            RemoteImage.new_platform_image(
                "test",
                tag="beta",
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            ),
            RemoteImage.new_platform_image(
                "test",
                tag="gamma",
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            ),
        }

    @pytest.mark.skipif(
        sys.platform == "win32", reason="aiodocker doesn't support Windows pipes yet"
    )
    async def test_tag_info(
        self, aiohttp_server: _TestServerFactory, make_client: _MakeClient
    ) -> None:
        JSON = {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {
                "mediaType": "application/vnd.docker.container.image.v1+json",
                "size": 349,
                "digest": "sha256:ignored-1",
            },
            "layers": [
                {
                    "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                    "size": 32036078,
                    "digest": "sha256:ignored-2",
                },
                {
                    "mediaType": "application/vnd.docker.image.rootfs.diff.tar.gzip",
                    "size": 854454,
                    "digest": "sha256:ignored-3",
                },
            ],
        }

        async def handler(request: web.Request) -> web.Response:
            assert (
                request.headers["Accept"]
                == "application/vnd.docker.distribution.manifest.v2+json"
            )
            return web.json_response(JSON)

        app = web.Application()
        app.router.add_get("/v2/project/test/manifests/test_tag", handler)

        srv = await aiohttp_server(app)
        url = "http://platform"
        registry_url = srv.make_url("/v2/")

        async with make_client(url, registry_url=registry_url) as client:
            image = RemoteImage.new_platform_image(
                name="test",
                tag="test_tag",
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            )
            ret = await client.images.tag_info(image)
            assert image.tag

        assert ret == Tag(name=image.tag, size=32890532)

    @pytest.mark.skipif(
        sys.platform == "win32", reason="aiodocker doesn't support Windows pipes yet"
    )
    async def test_tags_bad_image_with_tag(self, make_client: _MakeClient) -> None:
        url = URL("http://whatever")
        registry_url = URL("http://whatever-registry")
        async with make_client(url, registry_url=registry_url) as client:
            image = RemoteImage.new_platform_image(
                name="ubuntu",
                tag="latest",
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            )
            with pytest.raises(ValueError, match="tag is not allowed"):
                await client.images.tags(image)

    @pytest.mark.skipif(
        sys.platform == "win32", reason="aiodocker doesn't support Windows pipes yet"
    )
    async def test_tags_bad_image_without_name(self, make_client: _MakeClient) -> None:
        url = URL("http://whatever")
        registry_url = URL("http://whatever-registry")
        async with make_client(url, registry_url=registry_url) as client:
            image = RemoteImage.new_platform_image(
                name="",
                tag=None,
                cluster_name="default",
                registry="reg",
                org_name=None,
                project_name="project",
            )
            with pytest.raises(ValueError, match="missing image name"):
                await client.images.tags(image)
