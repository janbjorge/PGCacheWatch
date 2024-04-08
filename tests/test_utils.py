import asyncio
import datetime
import time
from typing import get_args

import asyncpg
import pytest
from pgcachewatch import listeners, models, utils


@pytest.mark.parametrize("N", (1, 2, 8))
@pytest.mark.parametrize("operation", get_args(models.OPERATIONS))
async def test_emit_event(
    N: int,
    operation: models.OPERATIONS,
    pgconn: asyncpg.Connection,
    pgpool: asyncpg.Pool,
) -> None:
    channel = "test_emit_event"
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn, models.PGChannel(channel))
    await asyncio.gather(
        *[
            utils.emit_event(
                pgpool,
                models.Event(
                    channel=channel,
                    operation=operation,
                    sent_at=datetime.datetime.now(tz=datetime.timezone.utc),
                    table="placeholder",
                ),
            )
            for _ in range(N)
        ]
    )

    # Give a bit of leeway due IO network io.
    await asyncio.sleep(0.1)

    assert listener.qsize() == N
    events = [listener.get_nowait() for _ in range(N)]
    assert len(events) == N
    assert [e.operation for e in events].count(operation) == N


@pytest.mark.parametrize("max_iter", (100, 200, 500))
async def test_pick_until_deadline_max_iter(
    max_iter: int,
    pgconn: asyncpg.Connection,
) -> None:
    channel = "test_pick_until_deadline_max_iter"
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn, models.PGChannel(channel))

    items = list(range(max_iter * 2))
    for item in items:
        listener.put_nowait(item)  # type: ignore

    assert listener.qsize() == len(items)
    assert (
        len(
            list(
                utils.pick_until_deadline(
                    listener,
                    settings=models.DeadlineSetting(
                        max_iter=max_iter,
                        max_time=datetime.timedelta(days=1),
                    ),
                )
            )
        )
        == max_iter
    )


@pytest.mark.parametrize(
    "max_time",
    (
        datetime.timedelta(milliseconds=25),
        datetime.timedelta(milliseconds=50),
        datetime.timedelta(milliseconds=100),
    ),
)
async def test_pick_until_deadline_max_time(
    max_time: datetime.timedelta,
    monkeypatch: pytest.MonkeyPatch,
    pgconn: asyncpg.Connection,
) -> None:
    channel = "test_pick_until_deadline_max_time"
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn, models.PGChannel(channel))

    x = -1

    def always_get_noawit() -> int:
        nonlocal x
        x += 1
        return x

    monkeypatch.setattr(listener, "get_nowait", always_get_noawit)

    start = time.perf_counter()
    list(
        utils.pick_until_deadline(
            listener,
            settings=models.DeadlineSetting(
                max_iter=1_000_000_000,
                max_time=max_time,
            ),
        )
    )
    end = time.perf_counter()
    assert end - start >= max_time.total_seconds()
