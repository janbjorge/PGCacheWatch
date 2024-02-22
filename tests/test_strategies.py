import asyncio
import datetime

import asyncpg
import pytest
from pgcachewatch import listeners, models, strategies


@pytest.mark.parametrize("N", (4, 16, 64))
async def test_greedy_strategy(N: int, pgconn: asyncpg.Connection) -> None:
    channel = models.PGChannel("test_greedy_strategy")

    listener = listeners.PGEventQueue()
    await listener.connect(pgconn, channel)

    strategy = strategies.Greedy(
        listener=listener,
        predicate=lambda e: e.operation == "insert",
    )

    for _ in range(N):
        await listener.put(
            models.Event(
                operation="insert",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
                channel=channel,
            )
        )
        assert strategy.clear()

    for _ in range(N):
        await listener.put(
            models.Event(
                operation="update",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
                channel=channel,
            )
        )
        assert not strategy.clear()

    for _ in range(N):
        assert not strategy.clear()


@pytest.mark.parametrize("N", (4, 16, 64))
async def test_windowed_strategy(
    N: int,
    pgconn: asyncpg.Connection,
) -> None:
    channel = models.PGChannel("test_windowed_strategy")
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn, channel)
    strategy = strategies.Windowed(
        listener=listener, window=["insert", "update", "delete"]
    )

    # Right pattern insert -> update -> delete
    for _ in range(N):
        await listener.put(
            models.Event(
                channel=channel,
                operation="insert",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            )
        )
        await listener.put(
            models.Event(
                channel=channel,
                operation="update",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            )
        )
        await listener.put(
            models.Event(
                channel=channel,
                operation="delete",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            )
        )
        assert strategy.clear()

    # Falsy patteren, chain of nothing.
    for _ in range(N):
        assert not strategy.clear()

    # Falsy patteren, chain of inserts.
    for _ in range(N):
        await listener.put(
            models.Event(
                channel=channel,
                operation="insert",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            )
        )
        assert not strategy.clear()


@pytest.mark.parametrize("N", (4, 16, 64))
@pytest.mark.parametrize(
    "dt",
    (
        datetime.timedelta(milliseconds=5),
        datetime.timedelta(milliseconds=10),
    ),
)
async def test_timed_strategy(
    dt: datetime.timedelta,
    N: int,
    pgconn: asyncpg.Connection,
) -> None:
    channel = models.PGChannel("test_timed_strategy")
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn, channel)
    strategy = strategies.Timed(listener=listener, timedelta=dt)

    # Bursed spaced out accoring to min dt req. to trigger a refresh.
    for _ in range(N):
        await asyncio.sleep(dt.total_seconds())
        await listener.put(
            models.Event(
                channel=channel,
                operation="insert",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            )
        )
        assert strategy.clear()

    # Bursets to close to trigger a refresh.
    for _ in range(N):
        await listener.put(
            models.Event(
                channel=channel,
                operation="insert",
                sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                table="placeholder",
            )
        )
        assert not strategy.clear()

    # No evnets, no clear.
    for _ in range(N):
        assert not strategy.clear()
