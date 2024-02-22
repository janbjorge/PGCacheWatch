import asyncio
import datetime

import asyncpg
import fastapi
import pytest
from fastapi.testclient import TestClient
from pgcachewatch import decorators, listeners, models, strategies, utils


async def fastapitestapp(
    channel: models.PGChannel,
    pgconn: asyncpg.Connection,
) -> fastapi.FastAPI:
    app = fastapi.FastAPI()

    listener = listeners.PGEventQueue()
    await listener.connect(pgconn, channel)

    @decorators.cache(strategy=strategies.Greedy(listener=listener))
    async def slow_db_read() -> dict:
        await asyncio.sleep(0.1)  # sim. a slow db-query.
        return {"now": datetime.datetime.now().isoformat()}

    @app.get("/sysconf")
    async def sysconf() -> dict[str, str]:
        return await slow_db_read()

    return app


@pytest.mark.parametrize("N", (2, 4, 16))
async def test_fastapi(
    N: int,
    pgconn: asyncpg.Connection,
) -> None:
    # No cache invalidation evnets emitted, all timestamps should be the same.
    tc = TestClient(
        await fastapitestapp(
            models.PGChannel("test_fastapi"),
            pgconn,
        )
    )
    responses = set[str](tc.get("/sysconf").json()["now"] for _ in range(N))
    assert len(responses) == 1


@pytest.mark.parametrize("N", (4, 8, 16))
async def test_fastapi_invalidate_cache(
    N: int,
    pgconn: asyncpg.Connection,
) -> None:
    # Emits one cache invalidation event per call, number of uniq timestamps
    # should equal the number of calls(N).

    channel = models.PGChannel(f"test_fastapi_invalidate_cache_{N}")
    tc = TestClient(await fastapitestapp(channel, pgconn))

    responses = set[str]()
    for _ in range(N):
        responses.add(tc.get("/sysconf").json()["now"])
        await utils.emit_event(
            conn=pgconn,
            event=models.Event(
                channel=channel,
                operation="update",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            ),
        )
        await asyncio.sleep(0.01)  # allow some time for the evnet to propegate.
    assert len(responses) == N
