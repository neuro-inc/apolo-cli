import asyncio
import os
import re
import shlex
import subprocess
import sys
import uuid
from asyncio import AbstractEventLoop
from contextlib import suppress
from datetime import datetime, timedelta
from pathlib import Path
from time import sleep, time
from typing import Any, AsyncIterator, Callable, ContextManager, Dict, Iterator, Tuple
from uuid import uuid4

import aiodocker
import aiohttp
import pytest
from aiohttp.test_utils import unused_port
from re_assert import Matches
from yarl import URL

from apolo_sdk import Container, JobStatus, RemoteImage, Resources
from apolo_sdk import get as api_get

from tests.e2e import make_image_name
from tests.e2e.conftest import Helper

pytestmark = pytest.mark.e2e_job

SKIP_NON_LINUX = pytest.mark.skipif(
    sys.platform != "linux", reason="PTY tests require Linux box"
)

ALPINE_IMAGE_NAME = "ghcr.io/neuro-inc/alpine:latest"
UBUNTU_IMAGE_NAME = "ghcr.io/neuro-inc/ubuntu:latest"
NGINX_IMAGE_NAME = "ghcr.io/neuro-inc/nginx:latest"
MIN_PORT = 49152
MAX_PORT = 65535

ANSI_RE = re.compile(r"\033\[[;?0-9]*[a-zA-Z]")
OSC_RE = re.compile(r"\x1b]0;.+\x07")


def strip_ansi(s: str) -> str:
    s1 = ANSI_RE.sub("", s)
    s2 = OSC_RE.sub("", s1)
    s3 = s2.replace("\x1b[K", "")
    s4 = s3.replace("\x1b[!p", "")
    return s4


@pytest.mark.e2e
def test_job_run(helper: Helper) -> None:

    job_name = f"test-job-{os.urandom(5).hex()}"

    # Kill another active jobs with same name, if any
    # Pass --owner because --name without --owner is too slow for admin users.
    captured = helper.run_cli(
        ["-q", "job", "ls", "--owner", helper.username, "--name", job_name]
    )
    if captured.out:
        jobs_same_name = captured.out.split("\n")
        assert len(jobs_same_name) == 1, f"found multiple active jobs named {job_name}"
        job_id = jobs_same_name[0]
        helper.kill_job(job_id)

    # Remember original running jobs
    captured = helper.run_cli(
        ["job", "ls", "--status", "running", "--status", "pending"]
    )
    store_out_list = captured.out.split("\n")[1:]
    jobs_orig = [x.split("  ")[0] for x in store_out_list]

    captured = helper.run_cli_run_job(
        [
            "--http-port",
            "80",
            "--no-wait-start",
            "--restart",
            "never",
            "--name",
            job_name,
            UBUNTU_IMAGE_NAME,
            "--",
            # use unrolled notation to check shlex.join()
            "bash",
            "-c",
            "sleep 10m; false",
        ]
    )
    match = re.match("Job ID: (.+)", captured.out)
    assert match is not None
    job_id = match.group(1)
    assert job_id.startswith("job-")
    assert job_id not in jobs_orig
    assert f"Name: {job_name}" in captured.out

    # Check it is in a running,pending job list now
    captured = helper.run_cli(
        ["-q", "job", "ls", "--status", "running", "--status", "pending"]
    )
    Matches(job_id) == captured.out

    # Wait until the job is running
    helper.wait_job_change_state_to(job_id, JobStatus.RUNNING)

    # Check that it is in a running job list
    captured = helper.run_cli(["-q", "job", "ls", "--status", "running"])
    Matches(job_id) == captured.out

    helper.kill_job(job_id, wait=False)


@pytest.mark.e2e
def test_job_rerun(helper: Helper) -> None:
    captured = helper.run_cli_run_job(
        [UBUNTU_IMAGE_NAME, "--", 'bash -c "exit 0"'],
        verbosity=-1,
    )
    job_id = captured.out

    helper.wait_job_change_state_to(
        job_id, JobStatus.SUCCEEDED, stop_state=JobStatus.FAILED
    )
    captured = helper.run_cli(
        [
            "-q",
            "job",
            "generate-run-command",
            job_id,
        ]
    )
    args = shlex.split(captured.out)
    captured = helper.run_cli(["-q", *args[1:]])
    job_id = captured.out
    helper.wait_job_change_state_to(
        job_id, JobStatus.SUCCEEDED, stop_state=JobStatus.FAILED
    )


@pytest.mark.e2e
def test_job_description(helper: Helper) -> None:
    # Remember original running jobs
    captured = helper.run_cli(["-q", "job", "ls", "--status", "running"])
    description = str(uuid4())
    # Run a new job
    command = "bash -c 'sleep 15m; false'"
    captured = helper.run_cli_run_job(
        [
            "--http-port",
            "80",
            "--description",
            description,
            "--no-wait-start",
            UBUNTU_IMAGE_NAME,
            "--",
            command,
        ]
    )
    match = re.match(r"Job ID:?\s+(.+)", captured.out)
    assert match is not None
    job_id = match.group(1)

    # Check it was not running before
    assert job_id.startswith("job-")

    # Wait until the job is running
    helper.wait_job_change_state_to(job_id, JobStatus.RUNNING, JobStatus.FAILED)

    # Check that it is in a running job list
    captured = helper.run_cli(
        ["job", "ls", "--status", "running", "--format", "{id}, {description}"]
    )
    store_out = captured.out
    assert job_id in store_out
    # Check that description is in the list
    assert description in store_out

    helper.kill_job(job_id, wait=False)


@pytest.mark.e2e
def test_job_filter_by_date_range(helper: Helper) -> None:
    captured = helper.run_cli_run_job(
        ["--no-wait-start", UBUNTU_IMAGE_NAME, "--", "sleep 300"]
    )
    match = re.match("Job ID: (.+)", captured.out)
    assert match is not None
    job_id = match.group(1)
    now = datetime.now()
    delta = timedelta(minutes=10)

    captured = helper.run_cli(["-q", "ps", "--since", (now - delta).isoformat()])
    jobs = {x.strip() for x in captured.out.split("\n")}
    assert job_id in jobs

    captured = helper.run_cli(["-q", "ps", "--since", (now + delta).isoformat()])
    jobs = {x.strip() for x in captured.out.split("\n")}
    assert job_id not in jobs

    captured = helper.run_cli(["-q", "ps", "--until", (now - delta).isoformat()])
    jobs = {x.strip() for x in captured.out.split("\n")}
    assert job_id not in jobs

    captured = helper.run_cli(["-q", "ps", "--until", (now + delta).isoformat()])
    jobs = {x.strip() for x in captured.out.split("\n")}
    assert job_id in jobs


@pytest.mark.e2e
def test_job_filter_by_tag(helper: Helper) -> None:
    tags = [f"test-tag:{uuid4()}", "test-tag:common"]
    tag_options = [key for pair in [("--tag", t) for t in tags] for key in pair]

    command = "sleep 10m"
    captured = helper.run_cli_run_job(
        [*tag_options, "--no-wait-start", UBUNTU_IMAGE_NAME, "--", command]
    )
    match = re.match("Job ID: (.+)", captured.out)
    assert match is not None
    job_id = match.group(1)

    captured = helper.run_cli(["-q", "ps", "--tag", tags[0]])
    jobs = {x.strip() for x in captured.out.split("\n")}
    assert job_id in jobs

    captured = helper.run_cli(["-q", "ps", "--tag", tags[1]])
    jobs = {x.strip() for x in captured.out.split("\n")}
    assert job_id in jobs

    captured = helper.run_cli(["-q", "ps", "--tag", "test-tag:not-present"])
    jobs = {x.strip() for x in captured.out.split("\n")}
    assert job_id not in jobs


@pytest.mark.e2e
def test_job_kill_non_existing(helper: Helper) -> None:
    # try to kill non existing job
    phantom_id = "not-a-job-id"
    expected_out = f"Cannot kill job {phantom_id}"
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(["job", "kill", phantom_id])
    assert cm.value.returncode == 1
    assert cm.value.stdout == ""
    killed_jobs = cm.value.stderr.splitlines()
    assert len(killed_jobs) == 1, killed_jobs
    assert killed_jobs[0].startswith(expected_out)


@pytest.mark.e2e
def test_e2e_no_env(helper: Helper) -> None:
    bash_script = 'echo "begin"$VAR"end"  | grep beginend'
    command = f"bash -c '{bash_script}'"
    captured = helper.run_cli_run_job(
        ["--no-wait-start", UBUNTU_IMAGE_NAME, "--", command]
    )

    out = captured.out
    match = re.match("Job ID: (.+)", out)
    assert match is not None
    job_id = match.group(1)

    helper.wait_job_change_state_from(job_id, JobStatus.PENDING)
    helper.wait_job_change_state_from(job_id, JobStatus.RUNNING)

    helper.assert_job_state(job_id, JobStatus.SUCCEEDED)


@pytest.mark.e2e
def test_e2e_env(helper: Helper) -> None:
    bash_script = 'echo "begin"$VAR"end"  | grep beginVALend'
    command = f"bash -c '{bash_script}'"
    captured = helper.run_cli_run_job(
        ["-e", "VAR=VAL", "--no-wait-start", UBUNTU_IMAGE_NAME, "--", command]
    )

    out = captured.out
    match = re.match("Job ID: (.+)", out)
    assert match is not None
    job_id = match.group(1)

    helper.wait_job_change_state_from(job_id, JobStatus.PENDING)
    helper.wait_job_change_state_from(job_id, JobStatus.RUNNING)

    helper.assert_job_state(job_id, JobStatus.SUCCEEDED)


@pytest.mark.e2e
def test_e2e_env_from_local(helper: Helper) -> None:
    os.environ["VAR"] = "VAL"
    bash_script = 'echo "begin"$VAR"end"  | grep beginVALend'
    command = f"bash -c '{bash_script}'"
    captured = helper.run_cli_run_job(
        ["-e", "VAR", "--no-wait-start", UBUNTU_IMAGE_NAME, "--", command]
    )

    out = captured.out
    match = re.match("Job ID: (.+)", out)
    assert match is not None
    job_id = match.group(1)

    helper.wait_job_change_state_from(job_id, JobStatus.PENDING)
    helper.wait_job_change_state_from(job_id, JobStatus.RUNNING)

    helper.assert_job_state(job_id, JobStatus.SUCCEEDED)


@pytest.mark.e2e
def test_e2e_multiple_env(helper: Helper) -> None:
    bash_script = 'echo begin"$VAR""$VAR2"end  | grep beginVALVAL2end'
    command = f"bash -c '{bash_script}'"
    captured = helper.run_cli_run_job(
        [
            "-e",
            "VAR=VAL",
            "-e",
            "VAR2=VAL2",
            "--no-wait-start",
            UBUNTU_IMAGE_NAME,
            "--",
            command,
        ]
    )

    out = captured.out
    match = re.match("Job ID: (.+)", out)
    assert match is not None
    job_id = match.group(1)

    helper.wait_job_change_state_from(job_id, JobStatus.PENDING)
    helper.wait_job_change_state_from(job_id, JobStatus.RUNNING)

    helper.assert_job_state(job_id, JobStatus.SUCCEEDED)


@pytest.mark.e2e
def test_e2e_multiple_env_from_file(helper: Helper, tmp_path: Path) -> None:
    env_file1 = tmp_path / "env_file1"
    env_file1.write_text("VAR2=LAV2\nVAR3=VAL3\n#VAR3=LAV3\nVAR4=LAV4\n\n")
    env_file2 = tmp_path / "env_file2"
    env_file2.write_text("VAR4=LAV4\nVAR4=VAL4")
    bash_script = (
        'echo begin"$VAR""$VAR2""$VAR3""$VAR4"end  | grep beginVALVAL2VAL3VAL4end'
    )
    command = f"bash -c '{bash_script}'"
    captured = helper.run_cli_run_job(
        [
            "-e",
            "VAR=VAL",
            "-e",
            "VAR2=VAL",
            "-e",
            "VAR2=VAL2",
            "--env-file",
            str(env_file1),
            "--env-file",
            str(env_file2),
            "--no-wait-start",
            UBUNTU_IMAGE_NAME,
            "--",
            command,
        ],
        verbosity=-1,
    )

    job_id = captured.out

    helper.wait_job_change_state_from(job_id, JobStatus.PENDING)
    helper.wait_job_change_state_from(job_id, JobStatus.RUNNING)

    helper.assert_job_state(job_id, JobStatus.SUCCEEDED)


@pytest.mark.e2e
def test_e2e_ssh_exec_true(helper: Helper) -> None:
    job_name = f"test-job-{str(uuid4())[:8]}"
    command = 'bash -c "sleep 15m; false"'
    job_id = helper.run_job_and_wait_state(UBUNTU_IMAGE_NAME, command, name=job_name)

    captured = helper.run_cli(
        [
            "--quiet",
            "job",
            "exec",
            "--no-tty",
            job_id,
            "--",
            # use unrolled notation to check shlex.join()
            "bash",
            "-c",
            "true",
        ]
    )
    assert captured.err == ""
    assert captured.out == ""
    helper.kill_job(job_id, wait=False)


@pytest.mark.e2e
def test_e2e_ssh_exec_false(helper: Helper) -> None:
    command = 'bash -c "sleep 15m; false"'
    job_id = helper.run_job_and_wait_state(UBUNTU_IMAGE_NAME, command)

    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(
            [
                "job",
                "exec",
                "--no-tty",
                job_id,
                "--",
                "bash -c 'echo test_e2e_ssh_exec_false; false'",
            ]
        )
    assert cm.value.returncode == 1
    helper.kill_job(job_id, wait=False)


@pytest.mark.e2e
def test_e2e_ssh_exec_no_cmd(helper: Helper) -> None:
    command = 'bash -c "sleep 15m; false"'
    job_id = helper.run_job_and_wait_state(UBUNTU_IMAGE_NAME, command)

    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(
            [
                "job",
                "exec",
                "--no-tty",
                job_id,
            ]
        )
    assert cm.value.returncode == 2
    helper.kill_job(job_id, wait=False)


@pytest.mark.e2e
@pytest.mark.skip(
    reason="ERROR: Command returned non-zero exit status 125: SSH execution problem"
)
def test_e2e_ssh_exec_echo(helper: Helper) -> None:
    command = 'bash -c "sleep 15m; false"'
    job_id = helper.run_job_and_wait_state(UBUNTU_IMAGE_NAME, command)

    for i in range(10):
        captured = helper.run_cli(
            [
                "--quiet",
                "job",
                "exec",
                "--no-tty",
                job_id,
                "--",
                'bash -c "sleep 30; echo ok"',
            ]
        )
        if captured.out == "":
            continue
        assert captured.err == ""
        assert captured.out == "ok"
        helper.kill_job(job_id, wait=False)
        break
    else:
        raise AssertionError(
            f"Cannot exec echo after 10 tries, the last output is {captured}"
        )


@pytest.mark.e2e
@SKIP_NON_LINUX
def test_e2e_ssh_exec_tty(helper: Helper) -> None:
    command = 'bash -c "sleep 15m; false"'
    job_id = helper.run_job_and_wait_state(UBUNTU_IMAGE_NAME, command)

    expect = helper.pexpect(
        [
            "--quiet",
            "job",
            "exec",
            job_id,
            "--",
            "[ -t 1 ]",
        ]
    )
    assert expect.wait() == 0
    helper.kill_job(job_id, wait=False)


@pytest.mark.e2e
def test_e2e_ssh_exec_no_job(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(
            [
                "job",
                "exec",
                "--no-tty",
                "job_id",
                "--",
                "true",
            ]
        )
    assert cm.value.returncode == 65


@pytest.mark.e2e
def test_e2e_ssh_exec_dead_job(helper: Helper) -> None:
    command = "true"
    job_id = helper.run_job_and_wait_state(
        UBUNTU_IMAGE_NAME, command, wait_state=JobStatus.SUCCEEDED
    )

    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli(
            [
                "job",
                "exec",
                "--no-tty",
                job_id,
                "--",
                "true",
            ]
        )
    assert cm.value.returncode == 72


@pytest.mark.e2e
@pytest.mark.skip(
    reason=(
        "ERROR: Command returned non-zero exit status 76: "
        "Unable to save job in current configuration"
    )
)
def test_job_save(request: Any, helper: Helper, docker: aiodocker.Docker) -> None:
    job_name = f"test-job-save-{uuid4().hex[:6]}"
    image_no_tag = make_image_name()
    image = f"{image_no_tag}:{job_name}"
    image_neuro_name_no_tag = f"image://{helper.cluster_uri_base}/{image_no_tag}"
    image_neuro_name = f"image://{helper.cluster_uri_base}/{image}"
    command = "sh -c 'echo -n 123 > /test; sleep 10m'"
    job_id_1 = helper.run_job_and_wait_state(
        ALPINE_IMAGE_NAME, command=command, wait_state=JobStatus.RUNNING
    )
    request.addfinalizer(
        lambda: helper.run_cli(["image", "rm", image_neuro_name_no_tag])
    )
    img_uri = f"image://{helper.cluster_uri_base}/{image}"
    captured = helper.run_cli(["job", "save", job_id_1, image_neuro_name])
    out = captured.out
    assert f"Saving job '{job_id_1}' to image '{img_uri}'..." in out
    assert f"Using remote image '{img_uri}'" in out
    assert "Creating image from the job container" in out
    assert "Image created" in out
    assert f"Using local image '{helper.username}/{image}'" in out
    assert "Pushing image..." in out
    assert out.endswith(img_uri)

    # wait to free the job name:
    helper.run_cli(["job", "kill", job_id_1])
    helper.wait_job_change_state_to(job_id_1, JobStatus.CANCELLED)

    command = 'sh -c \'[ "$(cat /test)" = "123" ]\''
    helper.run_job_and_wait_state(
        image_neuro_name, command=command, wait_state=JobStatus.SUCCEEDED
    )


@pytest.fixture
async def nginx_job_async(nmrc_path: Path) -> AsyncIterator[Tuple[str, str]]:
    async with api_get(path=nmrc_path) as client:
        secret = uuid4()
        command = (
            f"bash -c \"echo -n '{secret}' > /usr/share/nginx/html/secret.txt; "
            f"timeout -k 1m 15m /usr/sbin/nginx -g 'daemon off;'\""
        )
        container = Container(
            image=RemoteImage.new_external_image(
                name="ghcr.io/neuro-inc/nginx", tag="latest"
            ),
            command=command,
            resources=Resources(memory=100 * 2**20, cpu=0.1),
        )

        job = await client.jobs.run(
            container, scheduler_enabled=False, description="test NGINX job"
        )
        try:
            for i in range(300):  # Same as in helper.run_cli
                status = await client.jobs.status(job.id)
                if status.status == JobStatus.RUNNING:
                    break
                await asyncio.sleep(1)
            else:
                raise AssertionError(f"Cannot start NGINX job (job.id={job.id})")
            yield job.id, str(secret)
        finally:
            with suppress(Exception):
                await client.jobs.kill(job.id)


async def fetch_http(
    url: str, test: str, *, loop_sleep: float = 1.0, service_wait_time: float = 10 * 60
) -> int:
    status = 999
    start_time = time()
    async with aiohttp.ClientSession() as session:
        while status != 200 and (int(time() - start_time) < service_wait_time):
            try:
                async with session.get(url) as resp:
                    status = resp.status
                    text = await resp.text()
                    assert text == test, (
                        f"Secret not found "
                        f"via {url}. Like as it's not our test server."
                    )
            except aiohttp.ClientConnectionError:
                status = 599
            if status != 200:
                await asyncio.sleep(loop_sleep)
    return status


@pytest.mark.e2e
async def test_port_forward(helper: Helper, nginx_job_async: Tuple[str, str]) -> None:
    port = unused_port()
    job_id, secret = nginx_job_async

    proc = await helper.acli(["port-forward", job_id, f"{port}:80"])
    try:
        await asyncio.sleep(1)
        url = f"http://127.0.0.1:{port}/secret.txt"
        probe = await fetch_http(url, str(secret))
        assert probe == 200

        assert proc.returncode is None
    finally:
        proc.terminate()
        await proc.wait()


@pytest.mark.e2e
async def test_run_with_port_forward(helper: Helper) -> None:
    port = unused_port()
    job_id = None

    secret = uuid4()
    command = (
        f"bash -c \"echo -n '{secret}' > /usr/share/nginx/html/secret.txt; "
        f"timeout -k 1m 15m /usr/sbin/nginx -g 'daemon off;'\""
    )

    args = [
        "run",
        "--port-forward",
        f"{port}:80",
        "ghcr.io/neuro-inc/nginx:latest",
        "--",
        command,
    ]
    if helper.DEFAULT_PRESET:
        args[1:1] = ["-s", helper.DEFAULT_PRESET]

    proc = await helper.acli(args)
    try:
        await asyncio.sleep(1)
        url = f"http://127.0.0.1:{port}/secret.txt"
        probe = await fetch_http(url, str(secret))
        assert probe == 200

        assert proc.returncode is None
        assert proc.stdout is not None
        out = await proc.stdout.read(64 * 1024)
        job_id = helper.find_job_id(out.decode("utf-8", "replace"))
        assert job_id is not None
    finally:
        proc.terminate()
        await proc.wait()
        if job_id is not None:
            await helper.akill_job(job_id)


@pytest.mark.e2e
def test_job_submit_http_auth(
    helper: Helper, secret_job: Callable[..., Dict[str, Any]]
) -> None:
    loop_sleep = 1
    service_wait_time = 10 * 60
    auth_url = helper.get_config()._config_data.auth_config.auth_url

    async def _test_http_auth_redirect(url: URL) -> None:
        start_time = time()
        async with aiohttp.ClientSession() as session:
            while time() - start_time < service_wait_time:
                try:
                    async with session.get(url, allow_redirects=True) as resp:
                        if resp.status == 200 and resp.url.host == auth_url.host:
                            break
                except aiohttp.ClientConnectionError:
                    pass
                await asyncio.sleep(loop_sleep)
            else:
                raise AssertionError("HTTP Auth not detected")

    async def _test_http_auth_with_cookie(
        url: URL, cookies: Dict[str, str], secret: str
    ) -> None:
        start_time = time()
        ntries = 0
        async with aiohttp.ClientSession(cookies=cookies) as session:
            while time() - start_time < service_wait_time:
                try:
                    async with session.get(url, allow_redirects=False) as resp:
                        if resp.status == 200:
                            body = await resp.text()
                            if secret == body.strip():
                                break
                        ntries += 1
                        if ntries > 10:
                            raise AssertionError("Secret not match")
                except aiohttp.ClientConnectionError:
                    pass
                await asyncio.sleep(loop_sleep)
            else:
                raise AssertionError("Cannot fetch secret via forwarded http")

    http_job = secret_job(http_port=True, http_auth=True)
    ingress_secret_url = http_job["ingress_url"].with_path("/secret.txt")

    asyncio.run(_test_http_auth_redirect(ingress_secret_url))

    cookies = {"dat": helper.token}
    asyncio.run(
        _test_http_auth_with_cookie(ingress_secret_url, cookies, http_job["secret"])
    )


@pytest.mark.e2e
def test_job_run_exit_code(helper: Helper) -> None:
    # Run a new job
    command = 'bash -c "exit 101"'
    captured = helper.run_cli_run_job(
        ["--no-wait-start", UBUNTU_IMAGE_NAME, "--", command],
        verbosity=-1,
    )
    job_id = captured.out

    # Wait until the job is running
    helper.wait_job_change_state_to(job_id, JobStatus.FAILED)

    # Verify exit code is returned
    captured = helper.run_cli(["job", "status", job_id])
    store_out = captured.out
    Matches(r"Exit code\s+101") == store_out


@pytest.mark.parametrize("envvar", ["APOLO_PASSED_CONFIG", "NEURO_PASSED_CONFIG"])
@pytest.mark.e2e
def test_pass_config(envvar: str, helper: Helper) -> None:
    captured = helper.run_cli_run_job(
        [
            "--no-wait-start",
            "--pass-config",
            UBUNTU_IMAGE_NAME,
            "--",
            f'bash -c "sleep 15 && [ ! -z {envvar} ]"',
        ],
        verbosity=-1,
    )
    job_id = captured.out

    # fails if "test -f ..." check is not succeeded
    helper.wait_job_change_state_to(
        job_id, JobStatus.SUCCEEDED, stop_state=JobStatus.FAILED
    )


@pytest.mark.parametrize("http_auth", ["--http-auth", "--no-http-auth"])
@pytest.mark.e2e
def test_job_submit_bad_http_auth(helper: Helper, http_auth: str) -> None:
    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli_run_job(
            ["--http-port=0", http_auth, UBUNTU_IMAGE_NAME, "--", "true"]
        )
    assert cm.value.returncode == 2
    assert f"{http_auth} requires --http-port" in cm.value.stderr


@pytest.fixture
def fakebrowser(monkeypatch: Any) -> None:
    monkeypatch.setitem(os.environ, "BROWSER", "echo Browsing %s")


@pytest.mark.e2e
def test_job_browse(helper: Helper, fakebrowser: Any) -> None:
    # Run a new job
    captured = helper.run_cli_run_job(
        ["--detach", UBUNTU_IMAGE_NAME, "--", "true"],
        verbosity=-1,
    )
    job_id = captured.out

    captured = helper.run_cli(["-v", "job", "browse", job_id])
    assert "Browsing job, please open: https://job-" in captured.out


@pytest.mark.e2e
def test_job_run_browse(helper: Helper, fakebrowser: Any) -> None:
    # Run a new job
    captured = helper.run_cli_run_job(
        ["--detach", "--browse", UBUNTU_IMAGE_NAME, "--", "true"],
        verbosity=1,
    )
    assert "Browsing job, please open: https://job-" in captured.out


@pytest.mark.e2e
@pytest.mark.skip(
    reason="ERROR: AssertionError: job share permissions missing in output"
)
def test_job_run_share(helper: Helper, fakebrowser: Any) -> None:
    another_test_user = "test2"
    # Run a new job
    captured = helper.run_cli_run_job(
        [
            "--no-wait-start",
            "--share",
            another_test_user,
            UBUNTU_IMAGE_NAME,
            "--",
            "true",
        ],
        verbosity=-1,
    )
    job_id = captured.out.strip()

    uri = f"job://{helper.cluster_uri_base}/{job_id}"
    captured = helper.run_cli(["acl", "list", "--full-uri", "--shared", uri])
    result = [line.split() for line in captured.out.splitlines()]
    assert [uri, "write", another_test_user] in result

    helper.run_cli(["acl", "revoke", uri, another_test_user])


@pytest.mark.e2e
def test_job_submit_no_detach_failure(helper: Helper) -> None:
    # Run a new job
    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        helper.run_cli_run_job(
            ["--http-port", "80", UBUNTU_IMAGE_NAME, "--", "bash -c 'exit 127'"],
            verbosity=1,
        )
    assert exc_info.value.returncode == 127


@pytest.mark.e2e
def test_job_run_no_detach_browse_failure(helper: Helper) -> None:
    # Run a new job
    captured = None
    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        captured = helper.run_cli_run_job(
            ["--detach", "--browse", UBUNTU_IMAGE_NAME, "--", "bash -c 'exit 127'"],
            verbosity=1,
        )
    assert captured is None
    assert exc_info.value.returncode == 127


@pytest.mark.e2e
def test_job_run_volume_all(helper: Helper) -> None:
    root_mountpoint = "/var/neuro"
    cmd = " && ".join(
        [
            f"[ -d {root_mountpoint}/{helper.username} ]",
            f"[ -d {root_mountpoint}/neuromation ]",  # must be public
            f"[ $NEUROMATION_ROOT == {root_mountpoint} ]",
            f"[ $NEUROMATION_HOME == {root_mountpoint}/{helper.username} ]",
        ]
    )
    command = f"bash -c '{cmd}'"
    img = UBUNTU_IMAGE_NAME

    with pytest.raises(subprocess.CalledProcessError) as cm:
        helper.run_cli_run_job(["-T", "--volume=ALL", img, "--", command])
    assert cm.value.returncode == 127


@pytest.mark.e2e
def test_job_run_volume_all_and_another(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError):
        args = ["--volume", "ALL", "--volume", "storage::/home:ro"]
        captured = helper.run_cli_run_job([*args, UBUNTU_IMAGE_NAME, "--", "sleep 30"])
        msg = "Cannot use `--volume=ALL` together with other `--volume` options"
        assert msg in captured.err


def try_job_top(helper: Helper, *args: str) -> Iterator[str]:
    t0 = time()
    delay = 3.0
    while True:
        print("Try job top", delay)
        with pytest.raises(subprocess.CalledProcessError) as excinfo:
            helper.run_cli(["job", "top", "--timeout", str(delay), *args])
        stdout = excinfo.value.output
        stderr = excinfo.value.stderr
        print("STDOUT", stdout)
        assert excinfo.value.returncode == 124
        i = stdout.rfind(" ID/NAME ")
        yield (stdout if i < 0 else stdout[i:])
        if time() - t0 > 20 * 60:
            # timeout is reached without info from server
            raise AssertionError(
                f"Cannot get response from server "
                f"in {time() - t0} secs, delay={delay}\n"
                f"stdout = {stdout}\nstdderr = {stderr}"
            )
        print(f"job top has failed, increase timeout to {delay}")
        delay = min(delay * 1.5, 60)


@pytest.mark.e2e
def test_e2e_job_top(helper: Helper) -> None:
    command = "bash -c 'sleep 1000; echo test_e2e_job_top'"

    print("Run job... ")
    job_id = helper.run_job_and_wait_state(image=UBUNTU_IMAGE_NAME, command=command)
    print("... done")

    for stdout in try_job_top(helper, job_id):
        if job_id in stdout:
            # got response from job top telemetery
            break

    for stdout in try_job_top(helper, "--sort", "status,-memory", job_id):
        if job_id in stdout:
            # got response from job top telemetery
            break

    helper.kill_job(job_id, wait=True)

    # the "top" command formatter is tested by unit-tests


@pytest.mark.e2e
def test_e2e_job_top_filtering(helper: Helper, event_loop: AbstractEventLoop) -> None:
    job_name = f"test-job-{str(uuid4())[:8]}"
    description = str(uuid4())
    command = "bash -c 'sleep 1000; echo test_e2e_job_top_filtering'"

    print("Run jobs... ")
    job1_id = helper.run_job_and_wait_state(
        image=UBUNTU_IMAGE_NAME, command=command, description=description
    )
    job2_id = helper.run_job_and_wait_state(
        image=UBUNTU_IMAGE_NAME, command=command, name=job_name
    )
    print("... done")

    def _check1() -> None:
        for stdout in try_job_top(helper, "--name", job_name):
            if job2_id in stdout:
                # got response from job top telemetery
                assert job1_id not in stdout
                break

    def _check2() -> None:
        for stdout in try_job_top(helper, "--owner", helper.username):
            if job1_id in stdout and job2_id in stdout:
                # got response from job top telemetery
                break

    def _check3() -> None:
        for stdout in try_job_top(
            helper, "--owner", "ME", "--description", description
        ):
            if job1_id in stdout:
                # got response from job top telemetery
                assert job2_id not in stdout
                break

    def _check4() -> None:
        for stdout in try_job_top(
            helper, "--owner", helper.username, "--sort", "created"
        ):
            if job1_id in stdout and job2_id in stdout:
                # got response from job top telemetery
                assert stdout.index(job1_id) < stdout.index(job2_id)
                break

    def _check5() -> None:
        for stdout in try_job_top(
            helper, "--owner", helper.username, "--sort", "-created"
        ):
            if job1_id in stdout and job2_id in stdout:
                # got response from job top telemetery
                assert stdout.index(job1_id) > stdout.index(job2_id)
                break

    checks = [
        event_loop.run_in_executor(None, _check1),
        event_loop.run_in_executor(None, _check2),
        event_loop.run_in_executor(None, _check3),
        event_loop.run_in_executor(None, _check4),
        event_loop.run_in_executor(None, _check5),
    ]
    event_loop.run_until_complete(asyncio.gather(*checks))

    helper.kill_job(job1_id, wait=True)
    helper.kill_job(job2_id, wait=True)


@pytest.mark.e2e
def test_e2e_job_top_default_format(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        helper.run_cli(["job", "top", "--timeout", "0.1"])
    assert excinfo.value.returncode == 124
    stdout = excinfo.value.output
    assert "ID/NAME" in stdout
    assert "CPU" in stdout
    assert "GPU" in stdout
    assert "STATUS" not in stdout


@pytest.mark.e2e
def test_e2e_job_top_format(helper: Helper) -> None:
    with pytest.raises(subprocess.CalledProcessError) as excinfo:
        helper.run_cli(["job", "top", "--format", "name cpu", "--timeout", "0.1"])
    assert excinfo.value.returncode == 124
    stdout = excinfo.value.output
    assert "NAME" in stdout
    assert "CPU" in stdout
    assert "ID" not in stdout
    assert "GPU" not in stdout


@pytest.mark.e2e
def test_e2e_restart_failing(request: Any, helper: Helper) -> None:
    now = time()
    exit_after = int(now + 5 * 60)
    cmd = f"""
        if [[ `date +%s` -lt {exit_after} ]]
        then echo test_e2e_restart_failing
            false
        fi
        """
    cmd = "; ".join(line.strip() for line in cmd.strip().splitlines())

    captured = helper.run_cli_run_job(
        [
            "--restart",
            "on-failure",
            "--detach",
            UBUNTU_IMAGE_NAME,
            "--",
            f"bash -c '{cmd}'",
        ],
        verbosity=-1,
    )
    job_id = captured.out

    try:
        captured = helper.run_cli(["--color", "no", "job", "status", job_id])
        assert "on-failure" in captured.out

        helper.wait_job_change_state_to(job_id, JobStatus.RUNNING)
        sleep(1)
        helper.assert_job_state(job_id, JobStatus.RUNNING)
    finally:
        helper.kill_job(job_id)


@pytest.mark.e2e
def test_job_run_stdout(helper: Helper) -> None:
    command = 'bash -c "sleep 30; for count in {0..3}; do echo $count; sleep 1; done"'

    try:
        captured = helper.run_cli_run_job(
            ["--no-tty", UBUNTU_IMAGE_NAME, "--", command],
            verbosity=-1,
        )
    except subprocess.CalledProcessError as exc:
        # EX_IOERR is returned if the process is not finished in 10 secs after
        # disconnecting the attached session
        assert exc.returncode == 74
        err = exc.stderr
        out = exc.stdout
    else:
        err = captured.err
        out = captured.out

    assert err == ""
    assert "\n".join(f"{i}" for i in range(4)) in out


@pytest.mark.e2e
def test_job_attach_tty(helper: Helper) -> None:
    job_id = helper.run_job_and_wait_state(
        UBUNTU_IMAGE_NAME,
        "timeout -s KILL 15m bash --norc",
        tty=True,
        env={"PS1": "# "},
    )

    status = helper.job_info(job_id)
    assert status.container.tty

    expect = helper.pexpect(["job", "attach", job_id])
    expect.expect("========== Job is running in terminal mode =========")
    random_token = uuid4()
    expect.sendline(f"echo {random_token}\n")
    expect.expect(f"echo {random_token}")  # wait for cmd echo
    expect.expect(str(random_token))  # wait for cmd execution output

    helper.kill_job(job_id)


# The test doesn't work yet
# @pytest.mark.e2e
# def test_job_run_non_tty_stdin(helper: Helper) -> None:
#     command = "wc --chars"
#     captured = helper.run_cli_run_job(
#         [UBUNTU_IMAGE_NAME, "--", command], input="abcdef",
#         verbosity=-1,
#     )

#     assert captured.err == ""
#     assert captured.out == "6"


@pytest.mark.e2e
def test_job_secret_env(helper: Helper, secret: Tuple[str, str]) -> None:
    secret_name, secret_value = secret

    bash_script = f'echo "begin"$SECRET_VAR"end" | grep begin{secret_value}end'
    command = f"bash -c '{bash_script}'"
    captured = helper.run_cli_run_job(
        [
            "-e",
            f"SECRET_VAR=secret:{secret_name}",
            "--no-wait-start",
            UBUNTU_IMAGE_NAME,
            "--",
            command,
        ]
    )

    out = captured.out
    match = re.match("Job ID: (.+)", out)
    assert match is not None, captured
    job_id = match.group(1)

    helper.wait_job_change_state_to(job_id, JobStatus.SUCCEEDED, JobStatus.FAILED)


@pytest.mark.e2e
def test_job_secret_file(helper: Helper, secret: Tuple[str, str]) -> None:
    secret_name, secret_value = secret

    bash_script = (
        f'test -f /secrets/secretfile && grep "^{secret_value}$" /secrets/secretfile'
    )
    command = f"bash -c '{bash_script}'"
    captured = helper.run_cli_run_job(
        [
            "-v",
            f"secret:{secret_name}:/secrets/secretfile",
            "--no-wait-start",
            UBUNTU_IMAGE_NAME,
            "--",
            command,
        ]
    )

    out = captured.out
    match = re.match("Job ID: (.+)", out)
    assert match is not None, captured
    job_id = match.group(1)

    helper.wait_job_change_state_to(job_id, JobStatus.SUCCEEDED, JobStatus.FAILED)


@pytest.fixture
def secret(helper: Helper) -> Iterator[Tuple[str, str]]:
    secret_name = "secret" + str(uuid.uuid4()).replace("-", "")[:10]
    secret_value = str(uuid.uuid4())
    # Add secret
    cap = helper.run_cli(["secret", "add", secret_name, secret_value])
    assert cap.err == ""

    yield (secret_name, secret_value)

    # Remove secret
    cap = helper.run_cli(["secret", "rm", secret_name])
    assert cap.err == ""


@pytest.mark.e2e
def test_job_working_dir(helper: Helper) -> None:
    bash_script = '[ "x$(pwd)" == "x/var/log" ]'
    command = f"bash -c '{bash_script}'"
    captured = helper.run_cli_run_job(
        [
            "-w",
            "/var/log",
            "--no-wait-start",
            UBUNTU_IMAGE_NAME,
            "--",
            command,
        ],
        verbosity=-1,
    )

    job_id = captured.out

    helper.wait_job_change_state_to(job_id, JobStatus.SUCCEEDED, JobStatus.FAILED)


@pytest.mark.e2e
def test_job_disk_volume(
    helper: Helper, disk_factory: Callable[[str], ContextManager[str]]
) -> None:

    with disk_factory("1GB") as disk:
        bash_script = 'echo "test data" > /mnt/disk/file && cat /mnt/disk/file'
        command = f"bash -c '{bash_script}'"
        captured = helper.run_cli_run_job(
            [
                "--life-span",
                "1m",  # Avoid completed job to block disk from cleanup
                "-v",
                f"disk:{disk}:/mnt/disk:rw",
                "--no-wait-start",
                UBUNTU_IMAGE_NAME,
                "--",
                command,
            ]
        )

        out = captured.out
        match = re.match("Job ID: (.+)", out)
        assert match is not None, captured
        job_id = match.group(1)

        helper.wait_job_change_state_to(job_id, JobStatus.SUCCEEDED, JobStatus.FAILED)


@pytest.mark.e2e
def test_job_disk_volume_named(
    helper: Helper, disk_factory: Callable[[str, str], ContextManager[str]]
) -> None:
    disk_name = f"test-disk-{os.urandom(5).hex()}"

    with disk_factory("1G", disk_name):
        bash_script = 'echo "test data" > /mnt/disk/file && cat /mnt/disk/file'
        command = f"bash -c '{bash_script}'"
        captured = helper.run_cli_run_job(
            [
                "--life-span",
                "1m",  # Avoid completed job to block disk from cleanup
                "-v",
                f"disk:{disk_name}:/mnt/disk:rw",
                "--no-wait-start",
                UBUNTU_IMAGE_NAME,
                "--",
                command,
            ]
        )

        out = captured.out
        match = re.match("Job ID: (.+)", out)
        assert match is not None, captured
        job_id = match.group(1)

        helper.wait_job_change_state_to(job_id, JobStatus.SUCCEEDED, JobStatus.FAILED)
