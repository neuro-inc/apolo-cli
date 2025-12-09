import io
import json
import logging
import sys
from collections import namedtuple
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from yarl import URL

from apolo_sdk import CONFIG_ENV_NAME, Config

from apolo_cli.const import EX_OK
from apolo_cli.docker_credential_helper import main as dch
from apolo_cli.root import Root

SysCapWithCode = namedtuple("SysCapWithCode", ["out", "err", "code"])
log = logging.getLogger(__name__)


_RunCli = Callable[[list[str]], SysCapWithCode]


@pytest.fixture()
def config(root: Root) -> Config:
    return root.client.config


_RunDch = Callable[[list[str]], SysCapWithCode]


@pytest.fixture()
def run_dch(capfd: Any, monkeypatch: Any, tmp_path: Path, nmrc_path: Path) -> _RunDch:
    def _run_dch(arguments: list[str]) -> SysCapWithCode:

        log.info("Run 'docker-helper-apolo %s'", " ".join(arguments))
        code = EX_OK
        try:
            with monkeypatch.context() as ctx:
                ctx.setattr(sys, "argv", ["docker-credential-helper"] + arguments)
                ctx.setenv(CONFIG_ENV_NAME, str(nmrc_path))
                dch()
        except SystemExit as e:
            code = e.code  # type: ignore
        out, err = capfd.readouterr()
        return SysCapWithCode(out.strip(), err.strip(), code)

    return _run_dch


class TestCli:
    def test_path_not_exists(self, run_cli: _RunCli, tmp_path: Path) -> None:
        path = tmp_path / "some" / "not-exists"
        json_path = path / "config.json"
        capture = run_cli(["config", "docker", "--docker-config", str(path)])
        assert not capture.err
        assert json_path.is_file()

    def test_path_is_not_dir(self, run_cli: _RunCli, tmp_path: Path) -> None:
        path = tmp_path / "file"
        with path.open("w") as file:
            file.write("text")
        captured = run_cli(["config", "docker", "--docker-config", str(path)])
        assert captured.code
        assert captured.err

    def test_path_from_env(
        self, run_cli: _RunCli, tmp_path: Path, monkeypatch: Any, config: Config
    ) -> None:
        json_path = tmp_path / "config.json"
        with json_path.open("w") as file:
            file.write("{}")
        monkeypatch.setenv("DOCKER_CONFIG", str(tmp_path))
        capture = run_cli(["config", "docker"])
        assert not capture.err
        assert json_path.is_file()
        with json_path.open("rb") as fp:
            payload = json.load(fp)
        registry = URL(config.clusters[config.cluster_name].registry_url).host
        assert payload["credHelpers"] == {registry: "apolo"}

    def test_new_file(self, run_cli: _RunCli, tmp_path: Path, config: Config) -> None:
        path = tmp_path / ".docker"
        json_path = path / "config.json"
        capture = run_cli(["config", "docker", "--docker-config", str(path)])
        assert not capture.err
        assert json_path.is_file()
        with json_path.open("rb") as fp:
            payload = json.load(fp)
        registry = URL(config.clusters[config.cluster_name].registry_url).host
        assert payload["credHelpers"] == {registry: "apolo"}

    def test_merge_file_without_helpers(
        self, run_cli: _RunCli, tmp_path: Path, config: Config
    ) -> None:
        path = tmp_path / ".docker"
        path.mkdir()
        json_path = path / "config.json"
        with json_path.open("w", encoding="utf-8") as fp:
            json.dump({"test": "value\u20ac"}, fp)
        capture = run_cli(["config", "docker", "--docker-config", str(path)])
        assert not capture.err
        assert json_path.is_file()
        with json_path.open("rb") as fp2:
            payload = json.load(fp2)
        registry = URL(config.clusters[config.cluster_name].registry_url).host
        assert payload["credHelpers"] == {registry: "apolo"}
        assert payload["test"] == "value\u20ac"

    def test_merge_file_with_existing_helpers(
        self, run_cli: _RunCli, tmp_path: Path, config: Config
    ) -> None:
        path = tmp_path / ".docker"
        path.mkdir()
        json_path = path / "config.json"
        with json_path.open("w", encoding="utf-8") as fp:
            json.dump(
                {"test": "value\u20ac", "credHelpers": {"some.com": "handler"}}, fp
            )
        capture = run_cli(["config", "docker", "--docker-config", str(path)])
        assert not capture.err
        assert json_path.is_file()
        with json_path.open("rb") as fp2:
            payload = json.load(fp2)
        registry = URL(config.clusters[config.cluster_name].registry_url).host
        assert payload["credHelpers"] == {registry: "apolo", "some.com": "handler"}
        assert payload["test"] == "value\u20ac"

    def test_success_output_message(
        self, run_cli: _RunCli, tmp_path: Path, config: Config
    ) -> None:
        path = tmp_path / ".docker"
        json_path = path / "config.json"
        capture = run_cli(["config", "docker", "--docker-config", str(path)])
        assert not capture.err
        assert str(json_path) in capture.out.replace("\n", "")  # strip rich wrapping
        assert config.clusters[config.cluster_name].registry_url.host in capture.out


class TestHelper:
    def test_no_params_use(self, run_dch: _RunDch) -> None:
        capture = run_dch([])
        assert capture.code != EX_OK

    def test_too_mach_params(self, run_dch: _RunDch) -> None:
        capture = run_dch(["one", "two"])
        assert capture.code != EX_OK

    def test_unknown_operation(self, run_dch: _RunDch) -> None:
        capture = run_dch(["ping"])
        assert capture.code != EX_OK

    def test_store_operation(self, run_dch: _RunDch) -> None:
        capture = run_dch(["store"])
        assert capture.code != EX_OK

    def test_get_operation(
        self, run_dch: _RunDch, monkeypatch: Any, config: Config, token: str
    ) -> None:
        registry = config.clusters[config.cluster_name].registry_url.host
        assert registry is not None
        monkeypatch.setattr("sys.stdin", io.StringIO(registry))
        capture = run_dch(["get"])
        assert capture.code == EX_OK
        payload = json.loads(capture.out)
        assert payload == {"Username": "token", "Secret": token}
