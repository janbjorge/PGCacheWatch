import asyncio
import dataclasses
import datetime
import functools
import typing

import asyncpg
import pydantic

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


class DeadlineSetting(pydantic.BaseModel):
    """
    A data class representing settings for a deadline.

    Attributes:
        max_iter: Maximum number of iterations allowed.
        max_time: Maximum time allowed as a timedelta object.
    """

    max_iter: int = pydantic.Field(gt=0)
    max_time: datetime.timedelta

    @pydantic.model_validator(mode="after")
    def _max_time_gt_zero(self) -> "DeadlineSetting":
        if self.max_time <= datetime.timedelta(seconds=0):
            raise ValueError("max_time must be greater than zero")
        return self


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
