import asyncio
from typing import Any, Callable
from unittest.mock import MagicMock, Mock

import pytest

from neuromation import Job, Model, Storage
from neuromation.client.jobs import ResourceSharing


class AsyncContextManagerMock(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for key in ("aenter_return", "aexit_return"):
            setattr(self, key, kwargs[key] if key in kwargs else MagicMock())

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc:
            raise exc
        return self

    def coro_func(self, value: Any = None, exc: BaseException = None) -> asyncio.Future:
        f = asyncio.Future()
        f.set_result(value)
        if exc and not value:
            f.set_exception(exc)
        return f

    def patch(self, name: str, value: Any = None, exc: BaseException = None) -> None:
        self.__getattr__(name).return_value = self.coro_func(value, exc)

    def patch_func(self, mock: MagicMock, call_func: Callable) -> None:
        mock.side_effect = call_func


@pytest.fixture(scope="function")
def model(loop):
    model = Model(url="http://127.0.0.1", token="test-token-for-model", loop=loop)
    return model


@pytest.fixture(scope="function")
def storage(loop):
    storage = Storage(url="http://127.0.0.1", token="test-token-for-storage", loop=loop)
    return storage


@pytest.fixture(scope="function")
def jobs(loop):
    job = Job(url="http://127.0.0.1", token="test-token-for-job", loop=loop)
    return job


@pytest.fixture
def resource_sharing(loop):
    resource_sharing = ResourceSharing(
        url="http://127.0.0.1", token="test-token-for-job", loop=loop
    )
    return resource_sharing


@pytest.fixture(scope="function")
def mocked_store(loop):
    my_mock = AsyncContextManagerMock(Storage("no-url", "no-token", loop=loop))
    return my_mock


@pytest.fixture(scope="function")
def mocked_model(loop):
    my_mock = AsyncContextManagerMock(Model("no-url", "no-token", loop=loop))
    return my_mock


@pytest.fixture(scope="function")
def mocked_jobs(loop):
    my_mock = AsyncContextManagerMock(Job("no-url", "no-token", loop=loop))
    my_mock.submit = MagicMock()
    return my_mock


@pytest.fixture(scope="function")
def mocked_resource_share(loop):
    my_mock = AsyncContextManagerMock(ResourceSharing("no-url", "no-token", loop=loop))
    return my_mock


@pytest.fixture(scope="function")
def partial_mocked_store(mocked_store):
    def partial_mocked_store_func():
        return mocked_store

    return partial_mocked_store_func


@pytest.fixture(scope="function")
def partial_mocked_model(mocked_model):
    def partial_mocked_model_func():
        return mocked_model

    return partial_mocked_model_func


@pytest.fixture(scope="function")
def partial_mocked_job(mocked_jobs):
    def partial_mocked_jobs_func():
        return mocked_jobs

    return partial_mocked_jobs_func


@pytest.fixture(scope="function")
def partial_mocked_resource_share(mocked_resource_share):
    def partial_mocked_resource_share_func():
        return mocked_resource_share

    return partial_mocked_resource_share_func


@pytest.fixture(scope="function")
def http_storage(loop):
    storage = Storage(url="http://127.0.0.1", token="test-token-for-storage", loop=loop)
    return storage


@pytest.fixture(scope="function")
def http_backed_storage(http_storage):
    def partial_mocked_store():
        return http_storage

    return partial_mocked_store


@pytest.fixture
def setup_local_keyring(tmpdir, monkeypatch):

    import keyring
    import keyrings.cryptfile.file
    import keyrings.cryptfile.file_base

    def file_path():
        return str(tmpdir / "keystore")

    stored_keyring = keyring.get_keyring()
    keyring.set_keyring(keyrings.cryptfile.file.PlaintextKeyring())
    monkeypatch.setattr(
        keyrings.cryptfile.file_base.FileBacked, "file_path", file_path()
    )
    yield

    keyring.set_keyring(stored_keyring)


@pytest.fixture
def run(request, monkeypatch, capsys, tmpdir, setup_local_keyring):
    import sys
    from pathlib import Path

    def _home():
        return Path(tmpdir)

    def _run(arguments, rc_text):
        tmpdir.join(".nmrc").open("w").write(rc_text)

        monkeypatch.setattr(Path, "home", _home)
        monkeypatch.setattr(sys, "argv", ["nmc"] + arguments)

        from neuromation.cli import main

        return main(), capsys.readouterr()

    return _run
