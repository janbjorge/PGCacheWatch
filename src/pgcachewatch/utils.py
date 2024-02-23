import asyncio
import datetime
import functools
from typing import Generator, Hashable

import asyncpg

from pgcachewatch import listeners, models


def make_key(
    args: tuple[Hashable, ...],
    kwds: dict,
    typed: bool = False,
) -> Hashable:
    """
    Create a cache key from the given function arguments and keyword arguments.
    """
    return functools._make_key(args, kwds, typed)


async def emit_event(
    conn: asyncpg.Connection | asyncpg.Pool,
    event: models.Event,
) -> None:
    """
    Emit an event to the specified PostgreSQL channel.
    """
    await conn.execute(
        "SELECT pg_notify($1, $2)",
        event.channel,
        event.model_dump_json(),
    )


def pick_until_deadline(
    queue: listeners.EventQueueProtocol,
    settings: models.DeadlineSetting,
) -> Generator[models.Event, None, None]:
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
