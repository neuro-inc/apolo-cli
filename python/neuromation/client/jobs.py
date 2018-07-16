import asyncio
from contextlib import contextmanager
from io import BufferedReader
from typing import List

from dataclasses import dataclass

from neuromation.strings import parse

from .client import ApiClient
from .requests import (ContainerPayload, InferRequest, JobKillRequest,
                       JobListRequest, JobMonitorRequest, JobStatusRequest,
                       ResourcesPayload, TrainRequest)


@dataclass(frozen=True)
class Resources:
    memory: str
    cpu: int
    gpu: int


@dataclass(frozen=True)
class Image:
    image: str
    command: str


@dataclass(frozen=True)
class JobStatus:
    status: str
    id: str
    client: ApiClient
    url: str = ''

    async def _call(self):
        return JobStatus(
                client=self.client,
                **await self.client._fetch(
                    request=JobStatusRequest(
                        id=self.id
                    )))

    def wait(self, timeout=None):
        try:
            return self.client.loop.run_until_complete(
                asyncio.wait_for(
                    self._call(),
                    timeout=timeout
                    )
                )
        except asyncio.TimeoutError:
            raise TimeoutError


class Model(ApiClient):
    def infer(
            self,
            *,
            image: Image,
            resources: Resources,
            model: str,
            dataset: str,
            results: str)-> JobStatus:
        res = self._fetch_sync(
                InferRequest(
                    container=ContainerPayload(
                        image=image.image,
                        command=image.command,
                        resources=ResourcesPayload(
                            memory_mb=parse.to_megabytes(resources.memory),
                            cpu=float(resources.cpu),
                            gpu=float(resources.gpu))),
                    model_storage_uri=model,
                    dataset_storage_uri=dataset,
                    result_storage_uri=results))

        return JobStatus(
            id=res['job_id'],
            status=res['status'],
            client=self)

    def train(
            self,
            *,
            image: Image,
            resources: Resources,
            dataset: str,
            results: str) -> JobStatus:
        res = self._fetch_sync(
            TrainRequest(
                container=ContainerPayload(
                    image=image.image,
                    command=image.command,
                    resources=ResourcesPayload(
                        memory_mb=parse.to_megabytes(resources.memory),
                        cpu=float(resources.cpu),
                        )),
                dataset_storage_uri=dataset,
                result_storage_uri=results))

        return JobStatus(
            id=res['job_id'],
            status=res['status'],
            client=self)


class Job(ApiClient):
    def list(self) -> List[JobStatus]:
        res = self._fetch_sync(JobListRequest())
        return [
            JobStatus(
                client=self,
                id=job['id'],
                status=job['status'])
            for job in
            res['jobs']
        ]

    def kill(self, id: str):
        self._fetch_sync(JobKillRequest(id=id))
        # TODO(artyom, 07/16/2018): what are we returning here?
        return True

    @contextmanager
    def monitor(self, id: str) -> BufferedReader:
        with self._fetch_sync(JobMonitorRequest(id=id)) as content:
            yield BufferedReader(content)

    def status(self, id: str) -> JobStatus:
        res = self._fetch_sync(JobStatusRequest(id=id))
        return JobStatus(
            client=self,
            id=res['id'],
            status=res['status'])
