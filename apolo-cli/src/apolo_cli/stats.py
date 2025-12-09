# Google Measurement Protocol

import contextlib
import json
import logging
import os
import platform
import sqlite3
import sys
import time
import uuid
from urllib.parse import quote as urlquote
from urllib.parse import urlencode

from yarl import URL

from apolo_sdk import Client

import apolo_cli

logger = logging.getLogger(__name__)

GA_URL = URL("http://www.google-analytics.com/batch")
NEURO_EVENT_CATEGORY = "NEURO_EVENT_CATEGORY"

# Google Analytics supports up to 20 records in a batch
GA_CACHE_LIMIT = 20

SCHEMA = {
    "stats": "CREATE TABLE stats (cmd TEXT, args TEXT, timestamp REAL, version TEXT)",
    "uid": "CREATE TABLE uid (uid TEXT)",
}
DROP = {"stats": "DROP TABLE IF EXISTS stats", "uid": "DROP TABLE IF EXISTS uid"}

sqlite3_Row = sqlite3.Row


def ensure_schema(db: sqlite3.Connection) -> str:
    cur = db.cursor()
    ok = True
    found = set()
    cur.execute("SELECT type, name, sql from sqlite_master")
    for type, name, sql in cur:
        if type not in ("table", "index"):
            continue
        if name in SCHEMA:
            if SCHEMA[name] != sql:
                ok = False
                break
            else:
                found.add(name)

    if not ok or found < SCHEMA.keys():
        for sql in reversed(list(DROP.values())):
            cur.execute(sql)
        for sql in SCHEMA.values():
            cur.execute(sql)
    cur.execute("SELECT uid FROM uid")
    lst = list(cur)
    if len(lst) > 0:
        return lst[0][0]
    else:
        uid = str(uuid.uuid4())
        cur.execute("INSERT INTO uid (uid) VALUES (?)", (uid,))
        with contextlib.suppress(sqlite3.OperationalError):
            db.commit()
        return uid


def add_usage(
    db: sqlite3.Connection, cmd: str, args: list[dict[str, str | None]]
) -> None:
    cur = db.cursor()
    cur.execute(
        "INSERT INTO stats (cmd, args, timestamp, version) VALUES (?, ?, ?, ?)",
        (cmd, json.dumps(args), time.time(), apolo_cli.__version__),
    )


def select_oldest(
    db: sqlite3.Connection, *, limit: int = GA_CACHE_LIMIT, delay: float = 60
) -> list[sqlite3_Row]:
    # oldest 20 records
    old = list(
        db.execute(
            """
            SELECT ROWID, cmd, args, timestamp, version
            FROM stats ORDER BY timestamp ASC LIMIT ?
            """,
            (limit,),
        )
    )
    if old and len(old) < limit and old[-1]["timestamp"] > time.time() - delay:
        # A few data, the last recored is younger then one minute old;
        # don't send these data to google server
        old = []
    return old


def delete_oldest(db: sqlite3.Connection, old: list[sqlite3_Row]) -> None:
    db.executemany("DELETE FROM stats WHERE ROWID = ?", [[row["ROWID"]] for row in old])


def make_record(uid: str, url: URL, cmd: str, args: str, version: str) -> str:
    ec = os.environ.get(NEURO_EVENT_CATEGORY) or "CLI"

    # fmt: off
    ret = {
        "v": "1",                      # version
        "t": "event",                  # type
        "tid": "UA-106571369-3",       # tid
        "cid": uid,                    # client id, uuid4
        "ds": "cli",                   # data source, cli
        "ec": ec,                      # event category, CLI / WEB-CLI
        "ea": cmd,                     # event action, "apolo ps"
        "el": args,                    # event label, "[{}, {"all", true}]
        "an": "apolo",                 # application name, apolo
        "av": version,                 # application version, 20.01.15
        "aid": str(url),               # application id, https://api.dev.apolo.us/api/v1
    }
    # fmt: on
    return urlencode(ret, quote_via=urlquote)


async def send(client: Client, uid: str, data: list[sqlite3_Row]) -> None:
    if not data:
        return
    payload = (
        "\n".join(
            make_record(
                uid, client.config.api_url, row["cmd"], row["args"], row["version"]
            )
            for row in data
        )
        + "\n"
    )
    apolo_ver = apolo_cli.__version__
    plat = f"{sys.platform}/{platform.platform()}"
    py_version = platform.python_version()
    py_impl = platform.python_implementation()
    user_agent = f"ApoloCLI/{apolo_ver} ({plat}) Python/{py_version} ({py_impl})"
    async with client._session.post(
        GA_URL,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": user_agent,
        },
    ) as resp:
        await resp.read()  # drain response body


async def upload_gmp_stats(
    client: Client,
    cmd: str,
    args: list[dict[str, str | None]],
    skip_gmp_stats: bool,
) -> None:
    if skip_gmp_stats:
        return
    try:
        with client.config._open_db() as db:
            uid = ensure_schema(db)
            old = select_oldest(db)
            add_usage(db, cmd, args)
            with contextlib.suppress(sqlite3.OperationalError):
                db.commit()
        await send(client, uid, old)
        with client.config._open_db() as db:
            delete_oldest(db, old)
            with contextlib.suppress(sqlite3.OperationalError):
                db.commit()
    except sqlite3.DatabaseError as exc:
        if str(exc) != "database is locked":
            logger.warning("Cannot send the usage statistics: %s", repr(exc))
        else:
            logger.debug("Cannot send the usage statistics: %s", repr(exc))
