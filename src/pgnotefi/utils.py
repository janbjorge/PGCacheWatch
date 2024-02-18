import asyncio
import datetime
import functools
import typing

import asyncpg

from pgnotefi import listeners, models


def make_key(
    args: tuple[typing.Hashable, ...],
    kwds: dict,
    typed: bool = False,
) -> typing.Hashable:
    """
    Create a cache key from the given function arguments and keyword arguments.
    """
    return functools._make_key(args, kwds, typed)


async def emitevent(
    conn: asyncpg.Connection,
    event: models.Event,
) -> None:
    """
    Emit an event to the specified PostgreSQL channel.
    """
    await conn.execute(
        "SELECT pg_notify($1, $2)",
        event.channel,
        event.model_dump_json(exclude={"received_at"}),
    )


def pick_until_deadline(
    queue: listeners.PGEventQueue,
    settings: models.DeadlineSetting,
) -> typing.Iterator[models.Event]:
    """
    Yield events from the queue until the deadline is reached or queue is empty.
    """

    deadline = datetime.datetime.now() + settings.max_time
    iter_cnt = 0

    while settings.max_iter > iter_cnt and deadline > datetime.datetime.now():
        try:
            yield queue.get_nowait()
        except asyncio.QueueEmpty:
            return
        iter_cnt += 1
