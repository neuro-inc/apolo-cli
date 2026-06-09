import pytest

from apolo_cli import __version__

from tests.e2e import Helper


@pytest.mark.e2e
def test_print_version(helper: Helper) -> None:
    expected_out = f"Apolo Platform Client {__version__}"

    captured = helper.run_cli(["--version"])
    assert not captured.err
    assert captured.out == expected_out


@pytest.mark.e2e
def test_print_options(helper: Helper) -> None:
    captured = helper.run_cli(["--options"])
    assert not captured.err
    assert "Options" in captured.out


@pytest.mark.e2e
def test_print_config(helper: Helper) -> None:
    captured = helper.run_cli(["config", "show"])
    assert not captured.err
    assert "https://api.dev.apolo.us/api/v1" in captured.out


@pytest.mark.e2e
def test_print_config_token(helper: Helper) -> None:
    captured = helper.run_cli(["config", "show-token"])
    assert not captured.err
    assert captured.out  # some secure information was printed


@pytest.mark.e2e
def test_print_get_clusters(helper: Helper) -> None:
    captured = helper.run_cli(["config", "get-clusters"])
    assert not captured.err
    assert "Name: default" in captured.out
    assert "Presets" in captured.out


@pytest.mark.e2e
def test_root_trace_hide_token_default_true(helper: Helper) -> None:
    captured = helper.run_cli(["--trace", "ls"])
    assert "Authorization: Bearer " in captured.err
    assert "<hidden " in captured.err
    assert " chars>" in captured.err
