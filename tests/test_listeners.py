import asyncio
import datetime
from subprocess import Popen
from typing import get_args

import asyncpg
import pytest
import websockets
from conftest import pgb_address
from pgcachewatch import listeners, models, utils


@pytest.mark.parametrize("N", (1, 8, 32))
@pytest.mark.parametrize("operation", get_args(models.OPERATIONS))
async def test_eventqueue_and_pglistner(
    N: int,
    operation: models.OPERATIONS,
    pgconn: asyncpg.Connection,
    pgpool: asyncpg.Pool,
) -> None:
    channel = models.PGChannel(f"test_eventqueue_and_pglistner_{N}_{operation}")
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn, channel)

    to_emit = [
        models.Event(
            channel=models.PGChannel(channel),
            operation=operation,
            sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
            table="<placeholder>",
        )
        for _ in range(N)
    ]
    await asyncio.gather(*[utils.emit_event(pgpool, e) for e in to_emit])

    # Give a bit of leeway due IO network io.
    await asyncio.sleep(0.1)

    assert listener.qsize() == N

    # Due to use of gather(...) order can not be assumed, need to sort.
    assert to_emit == sorted(
        (listener.get_nowait() for _ in range(N)),
        key=lambda x: x.sent_at,
    )


@pytest.mark.parametrize("N", (1, 8, 32))
@pytest.mark.parametrize("operation", get_args(models.OPERATIONS))
async def test_eventqueue_and_wslistner(
    pgbapp: Popen,
    N: int,
    operation: models.OPERATIONS,
    pgpool: asyncpg.Pool,
) -> None:
    channel = models.PGChannel(f"test_eventqueue_and_pglistner_{N}_{operation}")
    listener = listeners.WSEventQueue()

    async with websockets.connect(f"ws://{pgb_address()}/pgpubsub/{channel}") as ws:
        await listener.connect(ws, channel)

        to_emit = [
            models.Event(
                channel=models.PGChannel(channel),
                operation=operation,
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="<placeholder>",
            )
            for _ in range(N)
        ]

        await asyncio.gather(*[utils.emit_event(pgpool, e) for e in to_emit])

        # Give a bit of leeway due IO network io.
        await asyncio.sleep(0.1)

        assert listener.qsize() == N

        # Due to use of gather(...) order can not be assumed, need to sort.
        assert to_emit == sorted(
            (listener.get_nowait() for _ in range(N)),
            key=lambda x: x.sent_at,
        )
