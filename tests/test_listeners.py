import asyncio
import datetime
import typing

import asyncpg
import pytest
from pgnotefi import env, listeners, models, utils


@pytest.mark.parametrize("N", (4, 8, 32))
@pytest.mark.parametrize("operation", typing.get_args(models.OPERATIONS))
async def test_eventqueue_and_pglistner(
    N: int,
    operation: models.OPERATIONS,
) -> None:
    assert (dsn := env.parsed.dsn)
    channel = models.PGChannel(f"test_eventqueue_and_pglistner_{N}_{operation}")
    eq = await listeners.PGEventQueue.create(channel)
    conn = await asyncpg.connect(dsn=str(dsn))

    for _ in range(N):
        await utils.emitevent(
            conn=conn,
            event=models.Event(
                channel=channel,
                operation=operation,
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            ),
        )
    await asyncio.sleep(0.01)
    evnets = set[models.Event]()
    while True:
        try:
            evnets.add(eq.get_nowait())
        except asyncio.QueueEmpty:
            break

    assert len(evnets) == N
    assert all(e.operation == operation for e in evnets)
