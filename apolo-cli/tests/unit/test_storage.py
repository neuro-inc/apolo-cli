from collections.abc import Callable
from pathlib import Path
from typing import Any

import toml

from apolo_sdk import Client, PluginManager

from apolo_cli.storage import calc_filters, calc_ignore_file_names

_MakeClient = Callable[..., Client]


async def test_calc_filters_section_doesnt_exist(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:

    async with make_client("https://example.com") as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        # empty config
        local_conf.write_text("")
        assert await calc_filters(client, None) == ()


async def test_calc_filters_user_spec(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str_list("storage", "cp-exclude")

    async with make_client(
        "https://example.com",
        plugin_manager=plugin_manager,
    ) as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        local_conf.write_text(
            toml.dumps({"storage": {"cp-exclude": ["*.jpg", "!main.jpg"]}})
        )
        assert await calc_filters(client, None) == (
            (True, "*.jpg"),
            (False, "main.jpg"),
        )


async def test_calc_filters_user_spec_and_options(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str_list("storage", "cp-exclude")

    async with make_client(
        "https://example.com",
        plugin_manager=plugin_manager,
    ) as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        local_conf.write_text(
            toml.dumps({"storage": {"cp-exclude": ["*.jpg", "!main.jpg"]}})
        )
        filters = ((False, "a*.jpg"), (True, "temp/"))
        assert await calc_filters(client, filters) == (
            (True, "*.jpg"),
            (False, "main.jpg"),
            (False, "a*.jpg"),
            (True, "temp/"),
        )


async def test_calc_ignore_file_names_default(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str_list("storage", "cp-exclude-from-files")

    async with make_client(
        "https://example.com",
        plugin_manager=plugin_manager,
    ) as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        # empty config
        local_conf.write_text("")
        assert await calc_ignore_file_names(client, None) == [
            ".apoloignore",
            ".neuroignore",
        ]
        local_conf.write_text(toml.dumps({"storage": {}}))
        assert await calc_ignore_file_names(client, None) == [
            ".apoloignore",
            ".neuroignore",
        ]


async def test_calc_ignore_file_names_user_spec(
    monkeypatch: Any, tmp_path: Path, make_client: _MakeClient
) -> None:
    plugin_manager = PluginManager()
    plugin_manager.config.define_str_list("storage", "cp-exclude-from-files")

    async with make_client(
        "https://example.com",
        plugin_manager=plugin_manager,
    ) as client:
        monkeypatch.chdir(tmp_path)
        local_conf = tmp_path / ".apolo.toml"
        local_conf.write_text(
            toml.dumps(
                {"storage": {"cp-exclude-from-files": [".gitignore", ".hgignore"]}}
            )
        )
        assert await calc_ignore_file_names(client, None) == [".gitignore", ".hgignore"]
