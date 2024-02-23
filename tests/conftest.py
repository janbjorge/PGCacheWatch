import os
from typing import AsyncGenerator

import asyncpg
import pytest


@pytest.fixture(scope="function")
async def pgconn() -> AsyncGenerator[asyncpg.Connection, None]:
    conn = await asyncpg.connect()
    try:
        yield conn
    finally:
        await conn.close()


@pytest.fixture(scope="function")
async def pgpool() -> AsyncGenerator[asyncpg.Pool, None]:
    async with asyncpg.create_pool() as pool:
        yield pool


@pytest.fixture(scope="function", autouse=True)
def set_pg_envs(monkeypatch: pytest.MonkeyPatch) -> None:
    Unset = object()

    if os.environ.get("PGHOST", Unset) is Unset:
        monkeypatch.setenv("PGHOST", "localhost")

    if os.environ.get("PGUSER", Unset) is Unset:
        monkeypatch.setenv("PGUSER", "testuser")

    if os.environ.get("PGPASSWORD", Unset) is Unset:
        monkeypatch.setenv("PGPASSWORD", "testpassword")

    if os.environ.get("PGDATABASE", Unset) is Unset:
        monkeypatch.setenv("PGDATABASE", "testdb")
