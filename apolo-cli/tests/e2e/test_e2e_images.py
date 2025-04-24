import asyncio
import re
import subprocess
import time
from dataclasses import replace
from pathlib import Path
from typing import Any, AsyncIterator, Set
from uuid import uuid4 as uuid

import aiodocker
import pytest
from yarl import URL

from apolo_sdk import CONFIG_ENV_NAME, DEFAULT_CONFIG_PATH, JobStatus

from tests.e2e import Helper, make_image_name


def parse_docker_ls_output(docker_ls_output: Any) -> Set[str]:
    return {
        repo_tag
        for info in docker_ls_output
        if info["RepoTags"] is not None
        for repo_tag in info["RepoTags"]
        if repo_tag
    }


@pytest.fixture()
def tag() -> str:
    return str(uuid())


async def generate_image(docker: aiodocker.Docker, tag: str) -> str:
    name = make_image_name()
    image_archive = Path(__file__).parent / "assets/echo-tag.tar"
    # TODO use random image name here
    image_name = f"{name}:{tag}"
    with image_archive.open(mode="r+b") as fileobj:
        await docker.images.build(
            fileobj=fileobj, tag=image_name, buildargs={"TAG": tag}, encoding="identity"
        )

    return image_name


@pytest.fixture()
async def image(docker: aiodocker.Docker, tag: str) -> AsyncIterator[str]:
    image = await generate_image(docker, tag)
    yield image
    await docker.images.delete(image, force=True)


@pytest.mark.skip("Skipping due to rate limit issues with image ls")
@pytest.mark.e2e
def test_images_complete_lifecycle(
    request: Any,
    helper: Helper,
    image: str,
    tag: str,
    event_loop: asyncio.AbstractEventLoop,
    docker: aiodocker.Docker,
) -> None:
    image_full_str = f"image://{helper.cluster_uri_base}/{image}"
    image_full_str_no_tag = image_full_str.replace(f":{tag}", "")
    request.addfinalizer(lambda: helper.run_cli(["image", "rm", image_full_str_no_tag]))
    # Let`s push image
    captured = helper.run_cli(["image", "push", image])
    event_loop.run_until_complete(
        docker.images.delete(f"{helper.registry_name_base}/{image}", force=True)
    )

    # stderr has "Used image ..." lines
    # assert not captured.err

    assert captured.out.endswith(image_full_str)
    image_url = URL(image_full_str)

    # Check if image available on registry
    image_full_str = f"image://{helper.cluster_uri_base}/{image}"
    image_short_str = f"image:{image}"
    assert captured.out.endswith(image_full_str)

    image_short_str_no_tag = image_short_str.replace(f":{tag}", "")

    # check ls short mode
    captured = helper.run_cli(["image", "ls"])
    assert image_short_str_no_tag in [
        line.strip() for line in captured.out.splitlines()
    ]

    captured = helper.run_cli(["image", "ls", "--full-uri"])
    assert image_full_str_no_tag in [line.strip() for line in captured.out.splitlines()]

    # check ls long mode
    captured = helper.run_cli(["image", "ls", "-l"])
    for line in captured.out.splitlines():
        if image_short_str_no_tag in line:
            break
    else:
        assert False, f"Not found {image_short_str_no_tag} in {captured.out}"

    # delete local
    event_loop.run_until_complete(docker.images.delete(image, force=True))
    docker_ls_output = event_loop.run_until_complete(docker.images.list())
    local_images = parse_docker_ls_output(docker_ls_output)
    assert image not in local_images

    # Pull image as with another tag
    captured = helper.run_cli(["image", "pull", f"image:{image}"])
    # stderr has "Used image ..." lines
    # assert not captured.err
    assert captured.out.endswith(image)

    # check pulled locally, delete for cleanup
    docker_ls_output = event_loop.run_until_complete(docker.images.list())
    local_images = parse_docker_ls_output(docker_ls_output)
    assert image in local_images

    # Execute image and check result
    captured = helper.run_cli_run_job(["--no-wait-start", str(image_url)], verbosity=-1)
    assert not captured.err
    job_id = captured.out
    assert job_id.startswith("job-")
    helper.wait_job_change_state_to(job_id, JobStatus.SUCCEEDED, JobStatus.FAILED)

    helper.check_job_output(job_id, re.escape(tag))


@pytest.mark.skip("Skipping due to rate limit issues with image ls")
@pytest.mark.e2e
def test_image_tags(
    request: Any,
    helper: Helper,
    image: str,
    tag: str,
    event_loop: asyncio.AbstractEventLoop,
    docker: aiodocker.Docker,
) -> None:
    image_full_str = f"image://{helper.cluster_uri_base}/{image}"
    image_full_str_no_tag = image_full_str.replace(f":{tag}", "")
    request.addfinalizer(lambda: helper.run_cli(["image", "rm", image_full_str_no_tag]))
    # push image
    captured = helper.run_cli(["image", "push", image])
    event_loop.run_until_complete(
        docker.images.delete(f"{helper.registry_name_base}/{image}", force=True)
    )

    assert captured.out.endswith(image_full_str)

    delay = 0
    t0 = time.time()

    while time.time() - t0 < 600:
        time.sleep(delay)
        # check the tag is present now
        try:
            captured = helper.run_cli(
                ["image", "tags", image_full_str_no_tag], timeout=300
            )
        except subprocess.TimeoutExpired:
            continue
        if tag in map(lambda s: s.strip(), captured.out.splitlines()):
            break
        # Give a chance to sync remote registries
        delay = min(delay * 2 + 1, 15)
    else:
        raise AssertionError(
            f"Delay is reached on waiting for tag {tag} in {captured.out}"
        )

    cmd = f"apolo image tags {image_full_str}"
    result = subprocess.run(cmd, capture_output=True, shell=True)
    assertion_msg = f"Command {cmd} should fail: {result.stdout!r} {result.stderr!r}"
    assert result.returncode, assertion_msg

    image_full_str_latest_tag = image_full_str.replace(f":{tag}", ":latest")
    cmd = f"apolo image tags {image_full_str_latest_tag}"
    result = subprocess.run(cmd, capture_output=True, shell=True)
    assertion_msg = f"Command {cmd} should fail: {result.stdout!r} {result.stderr!r}"
    assert result.returncode, assertion_msg


@pytest.mark.skip("Skipping due to rate limit issues with image ls")
@pytest.mark.e2e
async def test_images_delete(
    request: Any,
    helper: Helper,
    docker: aiodocker.Docker,
) -> None:
    image_ref = await generate_image(docker, tag="latest")
    name, _ = image_ref.split(":")
    img_name = f"image:{name}"

    helper.run_cli(["image", "push", image_ref])
    try:
        await docker.images.delete(image_ref, force=True)
        await docker.images.delete(
            f"{helper.registry_name_base}/{image_ref}", force=True
        )

        captured = helper.run_cli(["-q", "image", "ls"])
        assert img_name in captured.out
    finally:
        helper.run_cli(["image", "rm", img_name])

    for _ in range(10):
        captured = helper.run_cli(["-q", "image", "ls"])
        if img_name in captured.out:
            time.sleep(5)
        else:
            break

    assert img_name not in captured.out


@pytest.mark.skip("Skipping due to rate limit issues with image ls")
@pytest.mark.e2e
async def test_images_push_with_specified_name(
    request: Any,
    helper: Helper,
    image: str,
    tag: str,
    docker: aiodocker.Docker,
) -> None:
    # Let`s push image
    image_no_tag = image.replace(f":{tag}", "")
    pushed_no_tag = f"{image_no_tag}-pushed"
    pulled_no_tag = f"{image_no_tag}-pulled"
    pulled = f"{pulled_no_tag}:{tag}"
    request.addfinalizer(
        lambda: helper.run_cli(["image", "rm", f"image:{pushed_no_tag}"])
    )

    captured = helper.run_cli(["image", "push", image, f"image:{pushed_no_tag}:{tag}"])
    # stderr has "Used image ..." lines
    # assert not captured.err
    image_pushed_full_str = f"image://{helper.cluster_uri_base}/{pushed_no_tag}:{tag}"
    async with helper.client() as client:
        assert captured.out.endswith(image_pushed_full_str)

    # Check if image available on registry
    docker_ls_output = await docker.images.list()
    local_images = parse_docker_ls_output(docker_ls_output)
    assert pulled not in local_images

    async with helper.client() as client:
        image_pushed_full = client.parse.remote_image(image_pushed_full_str)
        image_url_without_tag = replace(image_pushed_full, tag=None)
        imgs = await client.images.list()
        assert image_url_without_tag in imgs

    # check locally
    docker_ls_output = await docker.images.list()
    local_images = parse_docker_ls_output(docker_ls_output)
    assert pulled not in local_images

    # Pull image as with another name
    captured = helper.run_cli(["image", "pull", f"image:{pushed_no_tag}:{tag}", pulled])
    try:
        # stderr has "Used image ..." lines
        # assert not captured.err
        assert captured.out.endswith(pulled)
        # check locally
        docker_ls_output = await docker.images.list()
        local_images = parse_docker_ls_output(docker_ls_output)
        assert pulled in local_images
    finally:
        await docker.images.delete(pulled, force=True)


@pytest.mark.skip("Skipping due to rate limit issues with image ls")
@pytest.mark.e2e
def test_docker_helper(
    request: Any,
    helper: Helper,
    image: str,
    tag: str,
    nmrc_path: Path,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv(CONFIG_ENV_NAME, str(nmrc_path or DEFAULT_CONFIG_PATH))
    helper.run_cli(["config", "docker"])
    full_tag = f"{helper.registry_name_base}/{image}"
    rmi_cmd = f"docker rmi {full_tag}"
    request.addfinalizer(
        lambda: subprocess.run(rmi_cmd, capture_output=True, shell=True)
    )
    tag_cmd = f"docker tag {image} {full_tag}"
    result = subprocess.run(tag_cmd, capture_output=True, shell=True)
    assert (
        result.returncode == 0
    ), f"Command {tag_cmd} failed: {result.stdout!r} {result.stderr!r} "
    image_url = f"image://{helper.cluster_uri_base}/{image}"
    image_full_str_no_tag = image_url.replace(f":{tag}", "")
    request.addfinalizer(lambda: helper.run_cli(["image", "rm", image_full_str_no_tag]))
    push_cmd = f"docker push {full_tag}"
    result = subprocess.run(push_cmd, capture_output=True, shell=True)
    assert (
        result.returncode == 0
    ), f"Command {push_cmd} failed: {result.stdout!r} {result.stderr!r} "
    # Run image and check output
    job_id = helper.run_job_and_wait_state(
        image_url, "", wait_state=JobStatus.SUCCEEDED, stop_state=JobStatus.FAILED
    )
    helper.check_job_output(job_id, re.escape(tag))
