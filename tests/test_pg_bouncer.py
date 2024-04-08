import asyncio
from datetime import datetime, timezone
from subprocess import Popen
from typing import get_args

import asyncpg
import pytest
import websockets
from conftest import pg_bouncer_isup, pgb_address
from pgcachewatch import listeners, models, utils


async def test_up_endpoint(pgbapp: Popen) -> None:
    assert await pg_bouncer_isup()


@pytest.mark.parametrize("operation", get_args(models.OPERATIONS))
@pytest.mark.parametrize("N", (1, 8))
async def test_ws_broadcast(
    pgbapp: Popen,
    N: int,
    pgpool: asyncpg.Pool,
    operation: models.OPERATIONS,
    channel: models.PGChannel = models.PGChannel("test_ws_broadcast"),
) -> None:
    async with websockets.connect(f"ws://{pgb_address()}/pgpubsub/{channel}") as ws:
        to_emit = [
            models.Event(
                channel=models.PGChannel(channel),
                operation=operation,
                sent_at=datetime.now(tz=timezone.utc),
                table="<placeholder>",
            )
            for _ in range(N)
        ]
        await asyncio.gather(*[utils.emit_event(pgpool, e) for e in to_emit])

        # Give a bit of leeway due IO network io.
        await asyncio.sleep(0.1)
        received = [models.Event.model_validate_json(x) for x in ws.messages]

        # Due to use of gather(...) order can be assumed, need to sort.
        assert to_emit == sorted(received, key=lambda x: x.sent_at)


@pytest.mark.parametrize("operation", get_args(models.OPERATIONS))
@pytest.mark.parametrize("N", (1, 8, 16))
async def test_put_ws_event_queue(
    N: int,
    operation: models.OPERATIONS,
    channel: models.PGChannel = models.PGChannel("test_put_ws_event_queue"),
) -> None:
    que = listeners.WSEventQueue()
    for _ in range(N):
        que.put_nowait(
            models.Event(
                channel=models.PGChannel(channel),
                operation=operation,
                sent_at=datetime.now(tz=timezone.utc),
                table="<placeholder>",
            )
        )

    assert que.qsize() == N

    que = listeners.WSEventQueue()
    for _ in range(N):
        await que.put(
            models.Event(
                channel=models.PGChannel(channel),
                operation=operation,
                sent_at=datetime.now(tz=timezone.utc),
                table="<placeholder>",
            )
        )
    assert que.qsize() == N

    que = listeners.WSEventQueue()
    await asyncio.gather(
        *[
            que.put(
                models.Event(
                    channel=models.PGChannel(channel),
                    operation=operation,
                    sent_at=datetime.now(tz=timezone.utc),
                    table="<placeholder>",
                )
            )
            for _ in range(N)
        ]
    )

    # Give a bit of leeway due IO network io.
    await asyncio.sleep(0.1)

    assert que.qsize() == N


@pytest.mark.parametrize("operation", get_args(models.OPERATIONS))
@pytest.mark.parametrize("N", (1, 64))
async def test_put_on_event_ws_event_queue(
    pgbapp: Popen,
    N: int,
    pgpool: asyncpg.Pool,
    operation: models.OPERATIONS,
    channel: models.PGChannel = models.PGChannel("test_put_on_event_ws_event_queue"),
) -> None:
    async with websockets.connect(f"ws://{pgb_address()}/pgpubsub/{channel}") as ws:
        lisn = listeners.WSEventQueue()
        await lisn.connect(ws, channel)

        to_emit = [
            models.Event(
                channel=models.PGChannel(channel),
                operation=operation,
                sent_at=datetime.now(tz=timezone.utc),
                table="<placeholder>",
            )
            for _ in range(N)
        ]

        await asyncio.gather(*[utils.emit_event(pgpool, e) for e in to_emit])

        # Give a bit of leeway due IO network io.
        await asyncio.sleep(0.1)

        assert lisn.qsize() == N
        # Due to use of gather(...) order can be assumed, need to sort.
        assert to_emit == sorted(
            (lisn.get_nowait() for _ in range(N)),
            key=lambda x: x.sent_at,
        )


async def test_ws_event_queue_connection_healthy(
    pgbapp: Popen,
    channel: models.PGChannel = models.PGChannel(
        "test_ws_event_queue_connection_healthy"
    ),
) -> None:
    async with websockets.connect(f"ws://{pgb_address()}/pgpubsub/{channel}") as ws:
        lisn = listeners.WSEventQueue()
        await lisn.connect(ws, channel)
        assert lisn.connection_healthy()

    assert not lisn.connection_healthy()
