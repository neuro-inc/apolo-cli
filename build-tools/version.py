#!/usr/bin/env python3
import abc
import dataclasses
import pathlib
import re
from typing import Dict

import click


class VersionProcessor(abc.ABC):
    @abc.abstractmethod
    def read(self, fname: pathlib.Path) -> str:
        pass

    @abc.abstractmethod
    def write(self, fname: pathlib.Path, version: str) -> None:
        pass


class InitVP(VersionProcessor):
    def read(self, fname: pathlib.Path) -> str:
        txt = fname.read_text()
        found = re.findall(r'^__version__ = "([^"]+)"\r?$', txt, re.M)
        if not found:
            raise click.ClickException(f"Unable to find version in {fname}.")
        if len(found) > 1:
            raise click.ClickException(f"Found multiple versions {found} in {fname}.")
        return found[0]

    def write(self, fname: pathlib.Path, version: str) -> None:
        # Check for possible errors
        old_version = self.read(fname)
        txt = fname.read_text()
        old = f'__version__ = "{old_version}"'
        new = f'__version__ = "{version}"'
        new_txt = txt.replace(old, new)
        fname.write_text(new_txt)


class SetupVP(VersionProcessor):
    def __init__(self, replace_sdk: bool = False) -> None:
        self._replace_sdk = replace_sdk

    def read(self, fname: pathlib.Path) -> str:
        txt = fname.read_text()
        found = re.findall(r'^    version="([^"]+)",\r?$', txt, re.M)
        if not found:
            raise click.ClickException(f"Unable to find version in {fname}.")
        if len(found) > 1:
            raise click.ClickException(f"Found multiple versions {found} in {fname}.")
        return found[0]

    def write(self, fname: pathlib.Path, version: str) -> None:
        # Check for possible errors
        old_version = self.read(fname)
        txt = fname.read_text()
        old = f'    version="{old_version}",'
        new = f'    version="{version}",'
        new_txt = txt.replace(old, new)
        if self._replace_sdk:
            old_dep = f'        "neuro-sdk>={old_version}",'
            if old_dep not in new_txt:
                raise click.ClickException(
                    f"Unable to find neuro-sdk dependency in {fname}."
                )
            new_dep = f'        "neuro-sdk>={version}",'
            new_txt = new_txt.replace(old_dep, new_dep)
        fname.write_text(new_txt)


FILES = {
    "neuro-sdk/neuro_sdk/__init__.py": InitVP(),
    "neuro-sdk/setup.py": SetupVP(False),
    "neuro-cli/neuro_cli/__init__.py": InitVP(),
    "neuro-cli/setup.py": SetupVP(True),
}


@dataclasses.dataclass(frozen=True)
class Config:
    root: pathlib.Path
    version: str
    files: Dict[str, VersionProcessor]


def find_root() -> pathlib.Path:
    here = pathlib.Path.cwd()
    while here.anchor != here:
        git = here / ".git"
        if git.exists() and git.is_dir():
            return here
        here = here.parent
    raise click.ClickException(f"Project root is not found for {here}")


def read_version(root: pathlib.Path) -> str:
    version_file = root / "VERSION.txt"
    txt = version_file.read_text()
    found = []
    for line in txt.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        found.append(line)
    if not found:
        raise click.ClickException(f"Version is not found in {version_file}")
    if len(found) > 1:
        raise click.ClickException(
            f"Multiple versions {found} are not found in {version_file}"
        )
    return found[0]


@click.group()
@click.pass_context
def main(ctx: click.Context):
    """Version commands"""
    root = find_root()
    version = read_version(root)
    files = {(root / fname): vp for fname, vp in FILES.items()}
    for fname in files.keys():
        if not fname.exists() or not fname.is_file():
            raise click.ClickException(f"File {fname} doesn't exist")
    ctx.obj = Config(root=root, version=version, files=files)


@main.command()
@click.pass_obj
def check(cfg: Config):
    """Check version"""
    for fname, vp in cfg.files.items():
        version = vp.read(fname)
        if version != cfg.version:
            raise click.ClickException(
                f"File {fname} contains version {version} but expected {cfg.version}, "
                "run './build-tools/version.py update' to fix the problem"
            )


@main.command()
@click.pass_obj
def update(cfg: Config):
    """Update version"""
    for fname, vp in cfg.files.items():
        vp.write(fname, cfg.version)


main()
