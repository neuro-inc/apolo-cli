from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import apolo_sdk


@asynccontextmanager
async def client() -> AsyncIterator[apolo_sdk.Client]:
    async with apolo_sdk.get() as c:
        yield c
