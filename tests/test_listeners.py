import asyncio
import datetime
from typing import get_args

import asyncpg
import pytest
from pgcachewatch import listeners, models, utils


@pytest.mark.parametrize("N", (4, 8, 32))
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

    for _ in range(N):
        await utils.emit_event(
            conn=pgpool,
            event=models.Event(
                channel=channel,
                operation=operation,
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            ),
        )
    await asyncio.sleep(0.01)
    evnets = list[models.Event]()
    while True:
        try:
            evnets.append(listener.get_nowait())
        except asyncio.QueueEmpty:
            break

    assert len(evnets) == N
    assert all(e.operation == operation for e in evnets)
