import asyncio
import datetime

import asyncpg
import fastapi
import pytest
from fastapi.testclient import TestClient
from pgcachewatch import decorators, env, listeners, models, strategies, utils


async def fastapitestapp(channel: models.PGChannel) -> fastapi.FastAPI:
    app = fastapi.FastAPI()

    listener = await listeners.PGEventQueue.create(channel)

    @decorators.cache(strategy=strategies.Gready(listener=listener))
    async def slow_db_read() -> dict:
        await asyncio.sleep(0.1)  # sim. a slow db-query.
        return {"now": datetime.datetime.now().isoformat()}

    @app.get("/sysconf")
    async def sysconf() -> dict[str, str]:
        return await slow_db_read()

    return app


@pytest.mark.parametrize("N", (2, 4, 16))
async def test_fastapi(N: int) -> None:
    # No cache invalidation evnets emitted, all timestamps should be the same.
    tc = TestClient(await fastapitestapp(models.PGChannel("test_fastapi")))
    responses = set[str](tc.get("/sysconf").json()["now"] for _ in range(N))
    assert len(responses) == 1


@pytest.mark.parametrize("N", (4, 8, 16))
async def test_fastapi_invalidate_cache(N: int) -> None:
    # Emits one cache invalidation event per call, number of uniq timestamps
    # should equal the number of calls(N).

    assert (dsn := env.parsed.dsn)
    conn = await asyncpg.connect(dsn=str(dsn))
    channel = models.PGChannel(f"test_fastapi_invalidate_cache_{N}")
    tc = TestClient(await fastapitestapp(channel))

    responses = set[str]()
    for _ in range(N):
        responses.add(tc.get("/sysconf").json()["now"])
        await utils.emitevent(
            conn=conn,
            event=models.Event(
                channel=channel,
                operation="update",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            ),
        )
        await asyncio.sleep(0.01)  # allow some time for the evnet to propegate.
    assert len(responses) == N
    await conn.close()
