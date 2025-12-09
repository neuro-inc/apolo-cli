import contextlib
import logging
import sqlite3
import sys
import time
from typing import Any, TypedDict

import dateutil.parser
from packaging.version import parse as parse_version
from yarl import URL

from ._config import Config
from ._core import _Core
from ._plugins import PluginManager
from ._utils import NoPublicConstructor

if sys.version_info >= (3, 10):
    from importlib.metadata import version
else:
    from importlib_metadata import version


class _Record(TypedDict):
    package: str
    version: str
    uploaded: float
    checked: float


log = logging.getLogger(__package__)


class VersionChecker(metaclass=NoPublicConstructor):
    _SCHEMA = {
        "pypi": "CREATE TABLE pypi "
        "(package TEXT, version TEXT, uploaded REAL, checked REAL)",
    }
    _DROP = {"pypi": "DROP TABLE IF EXISTS pypi"}
    _READ_PACKAGE = """
        SELECT package, version, uploaded, checked
        FROM pypi
        WHERE package = ?
        ORDER BY checked
        LIMIT 1
    """

    def __init__(
        self, core: _Core, config: Config, plugin_manager: PluginManager
    ) -> None:
        self._core = core
        self._config = config
        self._plugin_manager = plugin_manager
        self._records: dict[str, _Record] = {}
        self._loaded = False

    async def get_outdated(self) -> dict[str, str]:
        """Get packages that can be updated along with instructions for update.

        The information is collected from local database, updated by previous run.
        """
        await self._read_db()
        ret = {}
        for package, record in self._records.items():
            assert package == record["package"]
            spec = self._plugin_manager.version_checker._records.get(package)
            if spec is None:
                continue
            current = parse_version(version(package))
            pypi = parse_version(record["version"])
            if current < pypi and time.time() - record["uploaded"] > spec.delay:
                new_text = spec.update_text(str(current), str(pypi))
                if spec.exclusive:
                    return {package: new_text}
                else:
                    ret[package] = new_text
        return ret

    async def update(self) -> None:
        """Update local database with packages information fetched from pypi"""
        await self._read_db()
        inserts: list[tuple[str, str, float, float]] = []
        for package in self._plugin_manager.version_checker._records:
            record = self._records.get(package)
            await self._update_record(package, record, inserts)

        with self._config._open_db() as db:
            db.executemany(
                """
                INSERT INTO pypi (package, version, uploaded, checked)
                VALUES (?, ?, ?, ?)
            """,
                inserts,
            )
            db.execute(
                "DELETE FROM pypi WHERE checked < ?",
                (time.time() - 7 * 24 * 3600,),
            )
            with contextlib.suppress(sqlite3.OperationalError):
                db.commit()

    async def _read_db(self) -> None:
        if self._loaded:
            return
        with self._config._open_db() as db:
            self._ensure_schema(db)
            for package in self._plugin_manager.version_checker._records:
                record = self._read_package(db, package)
                if record is not None:
                    self._records[package] = record
        self._loaded = True

    async def _update_record(
        self,
        package: str,
        record: _Record | None,
        inserts: list[tuple[str, str, float, float]],
    ) -> None:
        if record is None or time.time() - record["checked"] > 10 * 60:
            pypi = await self._fetch_package(package)
            if pypi is None:
                return
            inserts.append(
                (
                    pypi["package"],
                    pypi["version"],
                    pypi["uploaded"],
                    pypi["checked"],
                )
            )
            self._records[pypi["package"]] = pypi

    def _ensure_schema(self, db: sqlite3.Connection) -> None:
        cur = db.cursor()
        ok = True
        found = set()
        cur.execute("SELECT type, name, sql from sqlite_master")
        for type, name, sql in cur:
            if type not in ("table", "index"):
                continue
            if name in self._SCHEMA:
                if self._SCHEMA[name] != sql:
                    ok = False
                    break
                else:
                    found.add(name)

        if not ok or found < self._SCHEMA.keys():
            for sql in reversed(list(self._DROP.values())):
                cur.execute(sql)
            for sql in self._SCHEMA.values():
                cur.execute(sql)

    def _read_package(self, db: sqlite3.Connection, package: str) -> _Record | None:
        cur = db.execute(self._READ_PACKAGE, (package,))
        return cur.fetchone()

    async def _fetch_package(
        self,
        package: str,
    ) -> _Record | None:
        url = URL(f"https://pypi.org/pypi/{package}/json")
        async with self._core._session.get(url) as resp:
            if resp.status != 200:
                log.debug("%s status on fetching %s", resp.status, url)
                return None
            pypi_response = await resp.json()
            ver = _parse_max_version(pypi_response)
            if ver is None:
                return None
            uploaded = _parse_version_upload_time(pypi_response, ver)
            return {
                "package": package,
                "version": ver,
                "uploaded": uploaded,
                "checked": time.time(),
            }


def _parse_date(value: str) -> float:
    # from format: "2019-08-19"
    return dateutil.parser.parse(value).timestamp()


def _parse_max_version(pypi_response: dict[str, Any]) -> str | None:
    try:
        ret = list(pypi_response["releases"].keys())
        return max(ver2 for ver2 in ret if not parse_version(ver2).is_prerelease)
    except (KeyError, ValueError):
        return None


def _parse_version_upload_time(
    pypi_response: dict[str, Any], target_version: str
) -> float:
    try:
        dates = [
            _parse_date(info["upload_time"])
            for ver, info_list in pypi_response["releases"].items()
            for info in info_list
            if ver == target_version
        ]
        return max(dates)
    except (KeyError, ValueError):
        return 0
