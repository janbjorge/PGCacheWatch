import asyncio
import datetime
import time
import typing

import asyncpg
import pytest
from pgnotefi import env, listeners, models, utils


@pytest.mark.parametrize("N", (1, 2, 8))
@pytest.mark.parametrize("operation", typing.get_args(models.OPERATIONS))
async def test_emitevent(N: int, operation: str) -> None:
    channel = "test_emitevent"
    listener = await listeners.PGEventQueue.create(models.PGChannel(channel))
    conn = await asyncpg.create_pool(dsn=str(env.parsed.dsn))
    await asyncio.gather(
        *[
            utils.emitevent(
                conn,
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

    assert listener.qsize() == N
    events = [listener.get_nowait() for _ in range(N)]
    assert len(events) == N
    assert [e.operation for e in events].count(operation) == N
    await listener._pgconn.close()
    await conn.close()


@pytest.mark.parametrize("max_iter", (100, 200, 500))
async def test_pick_until_deadline_max_iter(max_iter: int):
    channel = "test_pick_until_deadline_max_iter"
    listener = await listeners.PGEventQueue.create(models.PGChannel(channel))

    items = list(range(max_iter * 2))
    for item in items:
        listener.put_nowait(item)

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

    await listener._pgconn.close()


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
):
    channel = "test_pick_until_deadline_max_time"
    listener = await listeners.PGEventQueue.create(
        models.PGChannel(channel),
    )

    x = -1

    def always_get_noawit():
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
    await listener._pgconn.close()
