import asyncio
import dataclasses
import datetime
import functools
import typing

import asyncpg

from pgnotefi import listeners, models


def make_key(args: tuple, kwds: dict, typed: bool = False) -> typing.Hashable:
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
        event.json(exclude={"received_at"}),
    )


@dataclasses.dataclass(frozen=True)
class DeadlineSetting:
    """
    A data class representing settings for a deadline.

    Attributes:
        max_iter: Maximum number of iterations allowed.
        max_time: Maximum time allowed as a timedelta object.
    """

    max_iter: int
    max_time: datetime.timedelta

    def __post__init__(self):
        if self.max_iter < 0:
            raise ValueError("max_iter must be greather than zero.")
        if self.max_time < datetime.timedelta(seconds=0):
            raise ValueError("max_time must be greather than zero.")


def pick_until_deadline(
    queue: listeners.PGEventQueue,
    settings: DeadlineSetting,
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
