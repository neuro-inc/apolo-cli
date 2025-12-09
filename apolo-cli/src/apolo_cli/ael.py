# Attach / exec / logs utilities

import asyncio
import codecs
import enum
import logging
import signal
import sys
import threading
from collections.abc import Awaitable, Callable, Sequence
from contextlib import AsyncExitStack
from datetime import datetime
from typing import Any, NoReturn

import aiohttp
import click
from prompt_toolkit.formatted_text import HTML, merge_formatted_text
from prompt_toolkit.input import create_input
from prompt_toolkit.key_binding import KeyPress
from prompt_toolkit.key_binding.key_bindings import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.output import Output, create_output
from prompt_toolkit.shortcuts import PromptSession
from rich.markup import escape as rich_escape

from apolo_sdk import (
    JobDescription,
    JobStatus,
    ResourceNotFound,
    StdStream,
    StdStreamError,
)

from .const import EX_IOERR, EX_PLATFORMERROR
from .formatters.jobs import JobStopProgress
from .root import Root

log = logging.getLogger(__name__)


JOB_STARTED_NEURO_HAS_TTY = (
    "[green]√[/green] "
    "[dim]===== Job is running, press Ctrl-C to detach/kill =====[/dim]"
)

JOB_STARTED_NEURO_HAS_NO_TTY = (
    "[dim]===== Job is running, press Ctrl-C to detach =====[/dim]"
)

JOB_STARTED_TTY = "\n".join(
    "[green]√[/green] " + line
    for line in [
        "[dim]=========== Job is running in terminal mode ===========[/dim]",
        "[dim](If you don't see a command prompt, try pressing enter)[/dim]",
        "[dim](Use Ctrl-P Ctrl-Q key sequence to detach from the job)[/dim]",
    ]
)

ATTACH_STARTED_AFTER_LOGS = (
    "[dim]========= Job's output, may overlap with logs =========[/dim]"
)


class InterruptAction(enum.Enum):
    NOTHING = enum.auto()
    DETACH = enum.auto()
    KILL = enum.auto()


class AttachHelper:
    attach_ready: bool
    log_printed: bool
    job_started_msg: str
    write_sem: asyncio.Semaphore
    quiet: bool
    action: InterruptAction

    def __init__(self, *, quiet: bool) -> None:
        self.attach_ready = False
        self.log_printed = False
        self.job_started_msg = ""
        self.write_sem = asyncio.Semaphore()
        self.quiet = quiet
        self.action = InterruptAction.NOTHING


async def process_logs(
    root: Root,
    job: str,
    helper: AttachHelper | None,
    *,
    cluster_name: str | None,
    since: datetime | None = None,
    timestamps: bool = False,
) -> None:
    codec_info = codecs.lookup("utf8")
    decoder = codec_info.incrementaldecoder("replace")
    separator = "<================ Live logs ==============>"
    async with root.client.jobs.monitor(
        job,
        cluster_name=cluster_name,
        since=since,
        timestamps=timestamps,
        separator=separator,
        debug=root.verbosity >= 2,
    ) as it:
        async for chunk in it:
            if not chunk:
                txt = decoder.decode(b"", final=True)
                if not txt:
                    break
            else:
                txt = decoder.decode(chunk)
            if helper is not None:
                if helper.attach_ready:
                    return
                async with helper.write_sem:
                    if not helper.log_printed:
                        if not root.quiet:
                            root.print(helper.job_started_msg, markup=True)
                        helper.log_printed = True
                    sys.stdout.write(txt)
                    sys.stdout.flush()
            else:
                sys.stdout.write(txt)
                sys.stdout.flush()


async def process_exec(
    root: Root, job: str, cmd: str, tty: bool, *, cluster_name: str | None
) -> NoReturn:
    try:
        if tty:
            exit_code = await _exec_tty(root, job, cmd, cluster_name=cluster_name)
        else:
            exit_code = await _exec_non_tty(root, job, cmd, cluster_name=cluster_name)
    finally:
        root.soft_reset_tty()

    if not root.quiet:
        status = await root.client.jobs.status(job)
        print_job_result(root, status)

    sys.exit(exit_code)


async def _exec_tty(root: Root, job: str, cmd: str, *, cluster_name: str | None) -> int:
    loop = asyncio.get_event_loop()
    helper = AttachHelper(quiet=True)

    stdout = create_output()
    h, w = stdout.get_size()

    async with root.client.jobs.exec(
        job,
        cmd,
        tty=True,
        stdin=True,
        stdout=True,
        stderr=False,
        cluster_name=cluster_name,
    ) as stream:
        status = await root.client.jobs.status(job)

        if status.status is not JobStatus.RUNNING:
            raise ValueError(f"Job {job!r} is not running")

        await stream.resize(h=h, w=w)

        resize_task = loop.create_task(_process_resizing(stream.resize, stdout))
        input_task = loop.create_task(_process_stdin_tty(stream, helper))
        output_task = loop.create_task(
            _process_stdout_tty(root, stream, stdout, helper)
        )

        try:
            tasks = [resize_task, input_task, output_task]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            await root.cancel_with_logging(resize_task)
            await root.cancel_with_logging(input_task)
        return await _cancel_exec_output(root, output_task)


async def _exec_non_tty(
    root: Root, job: str, cmd: str, *, cluster_name: str | None
) -> int:
    loop = asyncio.get_event_loop()
    helper = AttachHelper(quiet=True)

    async with root.client.jobs.exec(
        job,
        cmd,
        tty=False,
        stdin=True,
        stdout=True,
        stderr=True,
        cluster_name=cluster_name,
    ) as stream:
        status = await root.client.jobs.status(job)

        if status.status is not JobStatus.RUNNING:
            raise ValueError(f"Job {job!r} is not running")

        input_task = None
        if root.tty:
            input_task = loop.create_task(_process_stdin_non_tty(root, stream))
        output_task = loop.create_task(_process_stdout_non_tty(root, stream, helper))

        try:
            tasks = [output_task]
            if input_task:
                tasks.append(input_task)
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            if input_task:
                await root.cancel_with_logging(input_task)
        return await _cancel_exec_output(root, output_task)


async def _cancel_exec_output(root: Root, output_task: "asyncio.Task[Any]") -> int:
    if output_task.done():
        ex = output_task.exception()
        if ex and isinstance(ex, StdStreamError):
            return ex.exit_code
    await root.cancel_with_logging(output_task)
    return EX_PLATFORMERROR


class RetryAttach(Exception):
    pass


async def process_attach(
    root: Root,
    job: JobDescription,
    tty: bool,
    logs: bool,
    port_forward: list[tuple[int, int]],
) -> None:
    max_retry_timeout = 10
    while True:
        retry_timeout = 1
        try:
            await _process_attach_single_try(root, job, tty, logs, port_forward)
        except RetryAttach:
            while True:
                root.print(f"Connection lost. Retrying in {retry_timeout} seconds")
                await asyncio.sleep(retry_timeout)
                retry_timeout = min(retry_timeout * 2, max_retry_timeout)
                try:
                    job = await root.client.jobs.status(job.id)
                except aiohttp.ClientConnectionError:
                    pass
                else:
                    break


async def _process_attach_single_try(
    root: Root,
    job: JobDescription,
    tty: bool,
    logs: bool,
    port_forward: list[tuple[int, int]],
) -> None:
    # Note, the job should be in running/finished state for this call,
    # passing pending job is forbidden

    while True:
        restarts = job.history.restarts
        async with AsyncExitStack() as stack:
            for local_port, job_port in port_forward:
                root.print(
                    f"Port localhost:{local_port} will be forwarded to port {job_port}"
                )
                await stack.enter_async_context(
                    root.client.jobs.port_forward(
                        job.id, local_port, job_port, cluster_name=job.cluster_name
                    )
                )

            helper = AttachHelper(quiet=root.quiet)
            if tty:
                helper.job_started_msg = JOB_STARTED_TTY
            elif root.tty:
                helper.job_started_msg = JOB_STARTED_NEURO_HAS_TTY
            else:
                helper.job_started_msg = JOB_STARTED_NEURO_HAS_NO_TTY
            loop = asyncio.get_event_loop()
            if logs:
                logs_printer = loop.create_task(
                    process_logs(root, job.id, helper, cluster_name=job.cluster_name)
                )
            else:
                # Placeholder, prints nothing
                logs_printer = loop.create_task(asyncio.sleep(0))

            try:
                job = await root.client.jobs.status(job.id)
                if job.status.is_finished:
                    await logs_printer
                    print_job_result(root, job)
                    if job.status == JobStatus.FAILED:
                        sys.exit(job.history.exit_code or EX_PLATFORMERROR)
                    else:
                        sys.exit(job.history.exit_code)

                if tty:
                    action = await _attach_tty(
                        root, job.id, helper, cluster_name=job.cluster_name
                    )
                else:
                    action = await _attach_non_tty(
                        root, job.id, helper, cluster_name=job.cluster_name
                    )

                if action == InterruptAction.KILL:
                    with JobStopProgress.create(
                        root.console, quiet=root.quiet
                    ) as progress:
                        progress.kill(job)
                    sys.exit(128 + signal.SIGINT)
                elif action == InterruptAction.DETACH:
                    with JobStopProgress.create(
                        root.console, quiet=root.quiet
                    ) as progress:
                        progress.detach(job)
                    sys.exit(0)
            except ResourceNotFound:
                # Container already stopped, so we can ignore such error.
                pass
            finally:
                await root.cancel_with_logging(logs_printer)
                root.soft_reset_tty()

            # We exited attach function not because of detach or kill,
            # probably we lost connectivity?
            try:
                job = await root.client.jobs.status(job.id)
            except aiohttp.ClientConnectionError:
                raise RetryAttach
            # Maybe it is spurious disconnect, and we should re-attach back?
            # Check container liveness by calling attach once
            try:
                async with root.client.jobs.attach(
                    job.id, stdin=True, cluster_name=job.cluster_name
                ):
                    raise RetryAttach
            except (asyncio.CancelledError, RetryAttach):
                raise
            except Exception:
                pass  # Was unable to reconnect, most likely container is dead

            # The class pins the current time in counstructor,
            # that's why we need to initialize
            # it AFTER the disconnection from attached session.
            with JobStopProgress.create(root.console, quiet=root.quiet) as progress:
                while (not job.status.is_finished) and (
                    job.history.reason == "Restarting"
                    or job.history.restarts == restarts
                ):
                    if not progress.step(job):
                        sys.exit(EX_IOERR)
                    await asyncio.sleep(0.2)
                    job = await root.client.jobs.status(job.id)
                progress.end(job)


async def _attach_tty(
    root: Root, job: str, helper: AttachHelper, *, cluster_name: str | None
) -> InterruptAction:
    stdout = create_output()
    h, w = stdout.get_size()

    async with root.client.jobs.attach(
        job, tty=True, stdin=True, stdout=True, stderr=False, cluster_name=cluster_name
    ) as stream:
        await stream.resize(h=h, w=w)

        loop = asyncio.get_event_loop()
        resize_task = loop.create_task(_process_resizing(stream.resize, stdout))
        input_task = loop.create_task(_process_stdin_tty(stream, helper))
        output_task = loop.create_task(
            _process_stdout_tty(root, stream, stdout, helper)
        )

        try:
            tasks = [resize_task, input_task, output_task]
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            await root.cancel_with_logging(resize_task)
            await root.cancel_with_logging(input_task)
            await _cancel_attach_output(root, output_task)

        return helper.action


async def _process_resizing(
    resizer: Callable[..., Awaitable[None]], stdout: Output
) -> None:
    loop = asyncio.get_event_loop()
    resize_event = asyncio.Event()

    def resize() -> None:
        resize_event.set()

    has_sigwinch = (
        hasattr(signal, "SIGWINCH")
        and threading.current_thread() is threading.main_thread()
    )
    if has_sigwinch:
        previous_winch_handler = signal.getsignal(signal.SIGWINCH)
        loop.add_signal_handler(signal.SIGWINCH, resize)
        if previous_winch_handler is None:
            # Borrowed from the Prompt Toolkit.
            # In some situations we receive `None`. This is
            # however not a valid value for passing to
            # `signal.signal` at the end of this block.
            previous_winch_handler = signal.SIG_DFL

    prevh = prevw = None
    try:
        while True:
            if has_sigwinch:
                await resize_event.wait()
                resize_event.clear()
            else:
                # Windows or non-main thread
                # The logic is borrowed from docker CLI.
                # Wait for 250 ms
                # If there is no resize event -- check the size anyway on timeout.
                # It makes resizing to work on Windows.
                await asyncio.sleep(0.25)
            h, w = stdout.get_size()
            if prevh != h or prevw != w:
                prevh = h
                prevw = w
                await resizer(w=w, h=h)
    finally:
        if has_sigwinch:
            loop.remove_signal_handler(signal.SIGWINCH)
            signal.signal(signal.SIGWINCH, previous_winch_handler)


def _has_detach(keys: Sequence[KeyPress], term: Sequence[Keys]) -> bool:
    for i in range(len(keys) - len(term) + 1):
        if keys[i].key == term[0]:
            for j in range(1, len(term)):
                if keys[i + j].key != term[j]:
                    break
            else:
                return True
    return False


async def _process_stdin_tty(stream: StdStream, helper: AttachHelper) -> None:
    ev = asyncio.Event()

    def read_ready() -> None:
        ev.set()

    term = (Keys.ControlP, Keys.ControlQ)
    prev: list[KeyPress] = []

    inp = create_input()
    with inp.raw_mode(), inp.attach(read_ready):
        while True:
            await ev.wait()
            ev.clear()
            if inp.closed:
                return
            keys = inp.read_keys()  # + inp.flush_keys()
            prev.extend(keys)
            if _has_detach(prev, term):
                helper.action = InterruptAction.DETACH
            if len(prev) >= len(term):
                oldest_key = len(prev) - len(term) + 1
                prev = prev[oldest_key:]
            buf = b"".join(key.data.encode("utf8") for key in keys)
            await stream.write_in(buf)
            if helper.action == InterruptAction.DETACH:
                return


async def _process_stdout_tty(
    root: Root, stream: StdStream, stdout: Output, helper: AttachHelper
) -> None:
    codec_info = codecs.lookup("utf8")
    decoder = codec_info.incrementaldecoder("replace")
    while True:
        chunk = await stream.read_out()
        if chunk is None:
            txt = decoder.decode(b"", final=True)
            if not txt:
                return
        else:
            txt = decoder.decode(chunk.data)
        async with helper.write_sem:
            if not helper.attach_ready:
                await _print_header(root, helper)
                helper.attach_ready = True
            stdout.write_raw(txt)
            stdout.flush()


async def _attach_non_tty(
    root: Root, job: str, helper: AttachHelper, *, cluster_name: str | None
) -> InterruptAction:
    async with root.client.jobs.attach(
        job, stdin=True, stdout=True, stderr=True, cluster_name=cluster_name
    ) as stream:
        input_task = None
        loop = asyncio.get_event_loop()
        if root.tty:
            input_task = loop.create_task(_process_stdin_non_tty(root, stream))
        output_task = loop.create_task(_process_stdout_non_tty(root, stream, helper))
        ctrl_c_task = loop.create_task(_process_ctrl_c(root, job, helper))

        try:
            tasks = [output_task, ctrl_c_task]
            if input_task:
                tasks.append(input_task)
            await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        finally:
            if input_task:
                await root.cancel_with_logging(input_task)
            await _cancel_attach_output(root, output_task)
            await root.cancel_with_logging(ctrl_c_task)
        return helper.action


async def _process_stdin_non_tty(root: Root, stream: StdStream) -> None:
    ev = asyncio.Event()

    def read_ready() -> None:
        ev.set()

    inp = create_input()
    with inp.attach(read_ready):
        while True:
            await ev.wait()
            ev.clear()
            if inp.closed:
                return
            keys = inp.read_keys()  # + inp.flush_keys()
            buf = b"".join(key.data.encode("utf8") for key in keys)
            await stream.write_in(buf)


async def _process_stdout_non_tty(
    root: Root, stream: StdStream, helper: AttachHelper
) -> None:
    codec_info = codecs.lookup("utf8")
    decoders = {
        1: codec_info.incrementaldecoder("replace"),
        2: codec_info.incrementaldecoder("replace"),
    }
    streams = {1: sys.stdout, 2: sys.stderr}

    async def _write(fileno: int, txt: str) -> None:
        f = streams[fileno]
        async with helper.write_sem:
            if not helper.attach_ready:
                await _print_header(root, helper)
                helper.attach_ready = True
            f.write(txt)
            f.flush()

    while True:
        chunk = await stream.read_out()
        if chunk is None:
            for fileno in (1, 2):
                txt = decoders[fileno].decode(b"", final=True)
                if txt:
                    await _write(fileno, txt)
            break
        else:
            txt = decoders[chunk.fileno].decode(chunk.data)
            await _write(chunk.fileno, txt)


async def _print_header(root: Root, helper: AttachHelper) -> None:
    if not helper.quiet and not helper.attach_ready:
        # Print header to stdout only,
        # logs are printed to stdout and never to
        # stderr (but logs printing is stopped by
        # helper.attach_ready = True regardless
        # what stream had receive text in attached mode.
        if helper.log_printed:
            s = ATTACH_STARTED_AFTER_LOGS
            if root.tty:
                s = "[green]√[/green] " + s
            root.print(s, markup=True)
        else:
            if not root.quiet:
                root.print(helper.job_started_msg, markup=True)


def _create_interruption_dialog() -> PromptSession[InterruptAction]:
    bindings = KeyBindings()

    @bindings.add(Keys.Enter)
    @bindings.add(Keys.Escape)
    def nothing(event: KeyPressEvent) -> None:
        event.app.exit(result=InterruptAction.NOTHING)

    @bindings.add("c-c")
    @bindings.add("C")
    @bindings.add("c")
    def kill(event: KeyPressEvent) -> None:
        event.app.exit(result=InterruptAction.KILL)

    @bindings.add("c-d")
    @bindings.add("D")
    @bindings.add("d")
    def detach(event: KeyPressEvent) -> None:
        event.app.exit(result=InterruptAction.DETACH)

    @bindings.add(Keys.Any)
    def _(event: KeyPressEvent) -> None:
        # Disallow inserting other text.
        pass

    message = HTML("  <b>Interrupted</b>. Please choose the action:\n")
    suffix = HTML(
        "<b>Ctrl-C</b> or <b>C</b> -- Kill\n"
        "<b>Ctrl-D</b> or <b>D</b> -- Detach \n"
        "<b>Enter</b> or <b>ESC</b> -- Continue the attached mode"
    )
    complete_message = merge_formatted_text([message, suffix])
    session: PromptSession[InterruptAction] = PromptSession(
        complete_message, key_bindings=bindings
    )
    return session


async def _process_ctrl_c(root: Root, job: str, helper: AttachHelper) -> None:
    # Exit from _process_ctrl_c() task finishes the outer _attach_non_tty() task
    # Return True if kill/detach was asked.
    # The returned value can be used for skipping the job termination
    queue: asyncio.Queue[int | None] = asyncio.Queue()
    loop = asyncio.get_event_loop()

    def on_signal(signum: int, frame: Any) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, signum)

    # Windows even loop has no add_signal_handler() method
    prev_signal = signal.signal(signal.SIGINT, on_signal)

    try:
        while True:
            getter = queue.get()
            if sys.platform == "win32":
                # On Python < 3.8 the interruption handling
                # responds not smoothly because the loop is blocked
                # in proactor for relative long time period.
                # Simple busy loop interrupts the proactor every 100 ms,
                # giving a chance to process other tasks
                getter = asyncio.wait_for(getter, 0.1)
            try:
                signum = await getter
            except asyncio.TimeoutError:
                continue
            if signum is None:
                return
            if not root.tty:
                click.secho("Detach terminal", dim=True, fg="green")
                helper.action = InterruptAction.DETACH
                return
            async with helper.write_sem:
                session = _create_interruption_dialog()
                answer = await session.prompt_async(set_exception_handler=False)
                if answer == InterruptAction.DETACH:
                    click.secho("Detach terminal", dim=True, fg="green")
                    helper.action = answer
                    return
                elif answer == InterruptAction.KILL:
                    click.secho("Kill job", fg="red")
                    await root.client.jobs.kill(job)
                    helper.action = answer
                    return
    finally:
        signal.signal(signal.SIGINT, prev_signal)


async def _cancel_attach_output(root: Root, output_task: "asyncio.Task[Any]") -> None:
    if output_task.done():
        ex = output_task.exception()
        if ex and isinstance(ex, StdStreamError):
            return
    await root.cancel_with_logging(output_task)


def print_job_result(root: Root, job: JobDescription) -> None:
    if job.status == JobStatus.SUCCEEDED and root.verbosity > 0:
        msg = f"Job [b]{job.id}[/b] finished successfully"
        if root.tty:
            msg = "[green]√[/green] " + msg
        root.print(msg, markup=True)
    if job.status == JobStatus.CANCELLED and root.verbosity >= 0:
        msg = f"Job [b]{job.id}[/b] was cancelled"
        if root.tty:
            msg = "[green]√[/green] " + msg
        if job.history.reason:
            msg += f" ({rich_escape(job.history.reason)})"
        root.print(msg, markup=True)
    if job.status == JobStatus.FAILED and root.verbosity >= 0:
        msg = f"Job [b]{job.id}[/b] failed"
        if root.tty:
            msg = "[red]×[/red] " + msg
        if job.history.reason:
            msg += f" ({rich_escape(job.history.reason)})"
        root.print(msg, markup=True)
