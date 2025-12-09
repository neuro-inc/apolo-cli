import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import random

DATETIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
LOGS_DIR = Path("~/.apolo/logs").expanduser()
FILE_FORMAT_PREFIX = "apolo-run-"
LOGS_ROTATION_DELAY = timedelta(days=3)


def get_handler() -> logging.FileHandler:
    if random() < 0.1:  # Only do cleanup for 10% of runs
        _do_rotation(LOGS_ROTATION_DELAY)
    return _get_handler()


_file_path_cached: Path | None = None


def get_log_file_path() -> Path:
    global _file_path_cached
    if _file_path_cached is None:
        now = datetime.now(timezone.utc)
        time_str = now.strftime(DATETIME_FORMAT)
        _file_path_cached = LOGS_DIR / f"{FILE_FORMAT_PREFIX}{time_str}.txt"
    return _file_path_cached


def _get_handler() -> logging.FileHandler:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return logging.FileHandler(get_log_file_path())


def _do_rotation(delay: timedelta) -> None:
    now = datetime.now(timezone.utc)
    if not LOGS_DIR.exists():
        return
    for log_file in LOGS_DIR.iterdir():
        if not log_file.is_file():
            continue
        time_str = log_file.stem[len(FILE_FORMAT_PREFIX) :]
        try:
            log_time = datetime.strptime(time_str, DATETIME_FORMAT)
        except ValueError:
            continue
        log_time = log_time.replace(tzinfo=timezone.utc)
        if log_time + delay < now:
            log_file.unlink()
