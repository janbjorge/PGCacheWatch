import asyncio
import os
from contextlib import suppress
from datetime import datetime, timedelta
from subprocess import PIPE, Popen
from typing import AsyncGenerator

import asyncpg
import httpx
import pytest


def pgb_address() -> str:
    return "127.0.0.1:8000"


async def pg_bouncer_isup() -> bool:
    timeout = timedelta(seconds=1)
    deadline = datetime.now() + timeout

    async with httpx.AsyncClient(base_url=f"http://{pgb_address()}") as client:
        while datetime.now() < deadline:
            with suppress(httpx.ConnectError):
                if (await client.get("/up")).is_success:
                    return True
            await asyncio.sleep(0.001)

    raise RuntimeError("Isup timeout")


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


@pytest.fixture(scope="function")
async def pgbapp() -> AsyncGenerator[Popen, None]:
    with Popen(
        "uvicorn pgcachewatch.pg_bouncer:main --factory".split(),
        stderr=PIPE,
        stdout=PIPE,
    ) as p:
        await pg_bouncer_isup()
        try:
            yield p
        finally:
            p.kill()
            p.wait()
