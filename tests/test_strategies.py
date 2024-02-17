import asyncio
import datetime

import pytest
from pgnotefi import listeners, models, strategies


@pytest.mark.asyncio
@pytest.mark.parametrize("N", (4, 16, 64))
async def test_gready_strategy(
    N: int,
    channel: models.PGChannel = models.PGChannel("test_gready_strategy"),
) -> None:
    listener = await listeners.PGEventQueue.create(channel)
    strategy = strategies.Gready(
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


@pytest.mark.asyncio
@pytest.mark.parametrize("N", (4, 16, 64))
async def test_windowed_strategy(
    N: int,
    channel: models.PGChannel = models.PGChannel("test_windowed_strategy"),
) -> None:
    listener = await listeners.PGEventQueue.create(channel)
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


@pytest.mark.asyncio
@pytest.mark.parametrize("N", (4, 16, 64))
@pytest.mark.parametrize(
    "dt",
    (
        datetime.timedelta(milliseconds=50),
        datetime.timedelta(milliseconds=100),
    ),
)
async def test_timed_strategy(
    dt: datetime.timedelta,
    N: int,
    channel: models.PGChannel = models.PGChannel("test_timed_strategy"),
) -> None:
    listener = await listeners.PGEventQueue.create(channel)
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
