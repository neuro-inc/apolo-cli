import pytest

from neuromation.cli.formatters.ftable import Align, ColumnWidth
from neuromation.cli.parse_utils import (
    COLUMNS,
    COLUMNS_MAP,
    JobColumnInfo,
    parse_columns,
    parse_memory,
)


def test_parse_memory() -> None:
    for value in ["1234", "   ", "", "-124", "M", "K", "k", "123B"]:
        with pytest.raises(ValueError, match=f"Unable parse value: {value}"):
            parse_memory(value)

    assert parse_memory("1K") == 1024
    assert parse_memory("2K") == 2048
    assert parse_memory("1kB") == 1000
    assert parse_memory("2kB") == 2000

    assert parse_memory("42M") == 42 * 1024 ** 2
    assert parse_memory("42MB") == 42 * 1000 ** 2

    assert parse_memory("42G") == 42 * 1024 ** 3
    assert parse_memory("42GB") == 42 * 1000 ** 3

    assert parse_memory("42T") == 42 * 1024 ** 4
    assert parse_memory("42TB") == 42 * 1000 ** 4

    assert parse_memory("42P") == 42 * 1024 ** 5
    assert parse_memory("42PB") == 42 * 1000 ** 5

    assert parse_memory("42E") == 42 * 1024 ** 6
    assert parse_memory("42EB") == 42 * 1000 ** 6

    assert parse_memory("42Z") == 42 * 1024 ** 7
    assert parse_memory("42ZB") == 42 * 1000 ** 7

    assert parse_memory("42Y") == 42 * 1024 ** 8
    assert parse_memory("42YB") == 42 * 1000 ** 8


def test_parse_columns_default():
    assert parse_columns("") == COLUMNS
    assert parse_columns(None) == COLUMNS


def test_parse_columns_short():
    ci = COLUMNS_MAP["id"]
    assert parse_columns("{id}") == [JobColumnInfo("id", ci.title, ci.align, ci.width)]


def test_parse_columns_sep():
    ci1 = COLUMNS_MAP["id"]
    ci2 = COLUMNS_MAP["name"]
    expected = [
        JobColumnInfo("id", ci1.title, ci1.align, ci1.width),
        JobColumnInfo("name", ci2.title, ci2.align, ci2.width),
    ]
    assert parse_columns("{id}{name}") == expected
    assert parse_columns("{id} {name}") == expected
    assert parse_columns("{id},{name}") == expected
    assert parse_columns("{id} ,{name}") == expected
    assert parse_columns("{id}, {name}") == expected
    assert parse_columns("{id} , {name}") == expected


def test_parse_columns_title():
    ci = COLUMNS_MAP["id"]
    assert parse_columns("{id;NEW_TITLE}") == [
        JobColumnInfo("id", "NEW_TITLE", ci.align, ci.width)
    ]


def test_parse_columns_props_full():
    assert parse_columns("{id;max=30;min=5;width=10;align=center;NEW_TITLE}") == [
        JobColumnInfo("id", "NEW_TITLE", Align.CENTER, ColumnWidth(5, 30, 10))
    ]


def test_parse_columns_props_subset():
    ci = COLUMNS_MAP["name"]
    assert parse_columns("{name;align=center;min=5}") == [
        JobColumnInfo(
            "name", ci.title, Align.CENTER, ColumnWidth(5, ci.width.max, ci.width.width)
        )
    ]


def test_parse_columns_invalid_format():
    with pytest.raises(ValueError, match="Invalid format"):
        parse_columns("{id")


def test_parse_columns_unknown():
    with pytest.raises(ValueError, match="Unknown column"):
        parse_columns("{unknown}")


def test_parse_columns_invalid_property():
    with pytest.raises(ValueError, match="Invalid property"):
        parse_columns("{id;min=abc}")
