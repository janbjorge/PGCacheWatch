import typing

import asyncpg
import pytest


@pytest.fixture(scope="function")
async def pgconn() -> typing.AsyncGenerator[asyncpg.Connection, None]:
    conn = await asyncpg.connect()
    yield conn
    await conn.close()


@pytest.fixture(scope="function")
async def pgpool() -> typing.AsyncGenerator[asyncpg.Pool, None]:
    async with asyncpg.create_pool() as pool:
        yield pool
