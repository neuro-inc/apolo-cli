import asyncio
import functools
import gc
import logging
import ssl
import warnings
from concurrent.futures import ThreadPoolExecutor
from types import TracebackType
from typing import (
    Any,
    AsyncContextManager,
    AsyncIterator,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    Type,
    TypeVar,
    final,
)

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)

logger = logging.getLogger(__name__)


@final
class Runner:
    def __init__(self, *, debug: bool = False) -> None:
        self._debug = debug
        self._started = False
        self._stopped = False
        self._executor = ThreadPoolExecutor()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def run(self, main: Awaitable[_T]) -> _T:
        assert self._started
        assert not self._stopped
        assert self._loop is not None
        if not asyncio.iscoroutine(main):
            raise ValueError(f"a coroutine was expected, got {main!r}")
        main_task = self._loop.create_task(main)

        return self._loop.run_until_complete(main_task)

    def __enter__(self) -> "Runner":
        assert not self._started
        assert not self._stopped
        self._started = True
        assert self._loop is None
        self._loop = asyncio.new_event_loop()
        self._loop.set_default_executor(self._executor)
        self._loop.set_debug(self._debug)
        if not self._debug:
            self._loop.set_exception_handler(_exception_handler)
        return self

    def __exit__(
        self, exc_type: Type[BaseException], exc_val: Exception, exc_tb: TracebackType
    ) -> None:
        assert self._started, "Loop was not started"
        assert self._loop is not None
        if self._stopped:
            return
        if self._loop.is_closed():
            return
        try:
            _cancel_all_tasks(self._loop)
            self._loop.run_until_complete(self._loop.shutdown_asyncgens())
        finally:
            # simple workaround for:
            # http://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", ResourceWarning)
                self._loop.close()
                del self._loop
                gc.collect()
            self._executor.shutdown(wait=True)
        self._stopped = True


def _exception_handler(
    loop: asyncio.AbstractEventLoop, context: Dict[str, Any]
) -> None:
    if context.get("message") in {
        "SSL error in data received",
        "Fatal error on transport",
    }:
        # validate we have the right exception, transport and protocol
        exception = context.get("exception")
        if isinstance(exception, ssl.SSLError) and exception.reason == "KRB5_S_INIT":
            return

    loop.default_exception_handler(context)


def _cancel_all_tasks(loop: asyncio.AbstractEventLoop) -> None:
    to_cancel = asyncio.all_tasks(loop)

    if not to_cancel:
        return

    for task in to_cancel:
        task.cancel()

    loop.run_until_complete(asyncio.gather(*to_cancel, return_exceptions=True))

    # temporary shut up the logger until aiohttp will be fixed
    # the message scares people :)
    return
    for task in to_cancel:
        if task.cancelled():
            continue
        if task.exception() is not None:
            loop.call_exception_handler(
                {
                    "message": "unhandled exception during asyncio.run() shutdown",
                    "exception": task.exception(),
                    "task": task,
                }
            )


# TODO (S Storchaka 2021-06-01): Methods __aiter__ and __anext__
# are supported for compatibility, but using the iterator without
# "async with" is strongly discouraged. In future these methods
# will be deprecated and finally removed. It will be just a context
# manager returning an iterator.
class _AsyncIteratorAndContextManager(
    Generic[_T_co],
    AsyncIterator[_T_co],
    AsyncContextManager[AsyncIterator[_T_co]],
):
    def __init__(self, gen: AsyncIterator[_T_co]) -> None:
        self._gen = gen

    async def __aenter__(self) -> AsyncIterator[_T_co]:
        return self._gen

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc: Optional[BaseException],
        tb: Optional[TracebackType],
    ) -> None:
        # Actually it is an AsyncGenerator.
        await self._gen.aclose()  # type: ignore

    def __aiter__(self) -> AsyncIterator[_T_co]:
        return self._gen.__aiter__()

    def __anext__(self) -> Awaitable[_T_co]:
        return self._gen.__anext__()


# XXX (S Storchaka 2021-06-01): The decorated function should actually
# return an AsyncGenerator, but all of our generator functions are annotated
# as returning an AsyncIterator.
def asyncgeneratorcontextmanager(
    func: Callable[..., AsyncIterator[_T_co]],
) -> Callable[..., _AsyncIteratorAndContextManager[_T_co]]:
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> _AsyncIteratorAndContextManager[_T_co]:
        gen = func(*args, **kwargs)
        return _AsyncIteratorAndContextManager[_T_co](gen)

    return wrapper
