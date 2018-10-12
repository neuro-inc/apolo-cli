from unittest.mock import patch

import aiohttp
import pytest

from neuromation import client
from neuromation.client.jobs import NetworkPortForwarding
from utils import (INFER_RESPONSE, TRAIN_RESPONSE, JsonResponse,
                   mocked_async_context_manager)

JOB_RESPONSE = {
    'status': 'SUCCEEDED',
    'id': 'iddqd',
}


@patch(
    'aiohttp.ClientSession.request',
    new=mocked_async_context_manager(JsonResponse(TRAIN_RESPONSE)))
def test_train_with_no_gpu(request, model, loop):
    result = model.train(
        image=client.Image(image='repo/image', command='bash'),
        resources=client.Resources(memory='16G', cpu=1.0, gpu=None, shm=None),
        dataset='schema://host/data',
        results='schema://host/results',
        network=None)

    aiohttp.ClientSession.request.assert_called_with(
            method='POST',
            data=None,
            params=None,
            json={
                'container': {
                    'image': 'repo/image',
                    'command': 'bash',
                    'resources': {'memory_mb': '16384', 'cpu': 1.0,
                                  'gpu': None,
                                  'shm': None},
                },
                'dataset_storage_uri': 'schema://host/data',
                'result_storage_uri': 'schema://host/results'},
            url='http://127.0.0.1/models')

    assert result == client.JobItem(
        client=model,
        status='PENDING',
        id='iddqd')


@patch(
    'aiohttp.ClientSession.request',
    new=mocked_async_context_manager(JsonResponse(TRAIN_RESPONSE)))
def test_train(request, model, loop):
    result = model.train(
        image=client.Image(image='repo/image', command='bash'),
        resources=client.Resources(memory='16G', cpu=1, gpu=1, shm=True),
        dataset='schema://host/data',
        results='schema://host/results',
        network=None)

    aiohttp.ClientSession.request.assert_called_with(
            method='POST',
            data=None,
            params=None,
            json={
                'container': {
                    'image': 'repo/image',
                    'command': 'bash',
                    'resources': {'memory_mb': '16384', 'cpu': 1.0,
                                  'gpu': 1.0,
                                  'shm': True},
                },
                'dataset_storage_uri': 'schema://host/data',
                'result_storage_uri': 'schema://host/results'},
            url='http://127.0.0.1/models')

    assert result == client.JobItem(
        client=model,
        status='PENDING',
        id='iddqd')


@patch(
    'aiohttp.ClientSession.request',
    new=mocked_async_context_manager(JsonResponse(TRAIN_RESPONSE)))
def test_train_with_http(request, model, loop):
    result = model.train(
        image=client.Image(image='repo/image', command='bash'),
        resources=client.Resources(memory='16G', cpu=1, gpu=1, shm=True),
        dataset='schema://host/data',
        results='schema://host/results',
        network=NetworkPortForwarding(
            {'http': 7878}
        )
    )

    aiohttp.ClientSession.request.assert_called_with(
            method='POST',
            data=None,
            params=None,
            json={
                'container': {
                    'image': 'repo/image',
                    'command': 'bash',
                    'http': {
                        'port': 7878
                    },
                    'resources': {'memory_mb': '16384', 'cpu': 1.0,
                                  'gpu': 1.0,
                                  'shm': True},
                },
                'dataset_storage_uri': 'schema://host/data',
                'result_storage_uri': 'schema://host/results'},
            url='http://127.0.0.1/models')

    assert result == client.JobItem(
        client=model,
        status='PENDING',
        id='iddqd')


@patch(
    'aiohttp.ClientSession.request',
    new=mocked_async_context_manager(JsonResponse(TRAIN_RESPONSE)))
def test_train_with_ssh(request, model, loop):
    result = model.train(
        image=client.Image(image='repo/image', command='bash'),
        resources=client.Resources(memory='16G', cpu=1, gpu=1, shm=True),
        dataset='schema://host/data',
        results='schema://host/results',
        network=NetworkPortForwarding(
            {'ssh': 7878}
        )
    )

    aiohttp.ClientSession.request.assert_called_with(
            method='POST',
            data=None,
            params=None,
            json={
                'container': {
                    'image': 'repo/image',
                    'command': 'bash',
                    'ssh': {
                        'port': 7878
                    },
                    'resources': {'memory_mb': '16384', 'cpu': 1.0,
                                  'gpu': 1.0,
                                  'shm': True},
                },
                'dataset_storage_uri': 'schema://host/data',
                'result_storage_uri': 'schema://host/results'},
            url='http://127.0.0.1/models')

    assert result == client.JobItem(
        client=model,
        status='PENDING',
        id='iddqd')


@patch(
    'aiohttp.ClientSession.request',
    new=mocked_async_context_manager(JsonResponse(TRAIN_RESPONSE)))
def test_train_with_ssh_and_http(request, model, loop):
    result = model.train(
        image=client.Image(image='repo/image', command='bash'),
        resources=client.Resources(memory='16G', cpu=1, gpu=1, shm=True),
        dataset='schema://host/data',
        results='schema://host/results',
        network=NetworkPortForwarding(
            {
                'ssh': 7878,
                'http': 8787
            }
        )
    )

    aiohttp.ClientSession.request.assert_called_with(
            method='POST',
            data=None,
            params=None,
            json={
                'container': {
                    'image': 'repo/image',
                    'command': 'bash',
                    'ssh': {
                        'port': 7878
                    },
                    'http': {
                        'port': 8787
                    },
                    'resources': {'memory_mb': '16384', 'cpu': 1.0,
                                  'gpu': 1.0,
                                  'shm': True},
                },
                'dataset_storage_uri': 'schema://host/data',
                'result_storage_uri': 'schema://host/results'},
            url='http://127.0.0.1/models')

    assert result == client.JobItem(
        client=model,
        status='PENDING',
        id='iddqd')


@patch(
    'aiohttp.ClientSession.request',
    new=mocked_async_context_manager(JsonResponse(INFER_RESPONSE)))
def test_infer(request, model, loop):
    result = model.infer(
        image=client.Image(image='repo/image', command='bash'),
        resources=client.Resources(memory='16G', cpu=1.0, gpu=1.0, shm=False),
        model='schema://host/model',
        dataset='schema://host/data',
        results='schema://host/results',
        network=None,
    )

    aiohttp.ClientSession.request.assert_called_with(
            method='POST',
            params=None,
            data=None,
            json={
                'container': {
                    'image': 'repo/image',
                    'command': 'bash',
                    'resources': {'memory_mb': '16384', 'cpu': 1.0,
                                  'gpu': 1.0,
                                  'shm': False},
                },
                'dataset_storage_uri': 'schema://host/data',
                'result_storage_uri': 'schema://host/results',
                'model_storage_uri': 'schema://host/model'},
            url='http://127.0.0.1/models')

    assert result == client.JobItem(
        client=model,
        status='PENDING',
        id='iddqd')


@patch(
    'aiohttp.ClientSession.request',
    new=mocked_async_context_manager(JsonResponse(JOB_RESPONSE)))
def test_job_status(request, model, loop):
    job = client.JobItem(
        client=model,
        **{
            **JOB_RESPONSE,
            'status': 'PENDING',
        })

    res = job.wait()
    assert res == client.JobItem(client=model, **JOB_RESPONSE)


@patch(
    'aiohttp.ClientSession.request',
    new=mocked_async_context_manager(JsonResponse(
        {'error': 'blah!'},
        error=aiohttp.ClientConnectionError()
    )))
def test_network_error_is_not_intercepted(storage):
    with pytest.raises(aiohttp.ClientError):
        storage.ls(path='blah')
