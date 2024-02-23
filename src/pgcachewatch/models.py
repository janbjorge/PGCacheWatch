import datetime
from typing import Literal, NewType

import pydantic

OPERATIONS = Literal[
    "insert",
    "update",
    "delete",
]

PGChannel = NewType(
    "PGChannel",
    str,
)


class DeadlineSetting(pydantic.BaseModel):
    """
    A data class representing settings for a deadline.

    Attributes:
        max_iter: Maximum number of iterations allowed.
        max_time: Maximum time allowed as a timedelta object.
    """

    max_iter: int = pydantic.Field(gt=0, default=1_000)
    max_time: datetime.timedelta = pydantic.Field(
        default=datetime.timedelta(milliseconds=1)
    )

    @pydantic.model_validator(mode="after")
    def _max_time_gt_zero(self) -> "DeadlineSetting":
        if self.max_time <= datetime.timedelta(seconds=0):
            raise ValueError("max_time must be greater than zero")
        return self


class Event(pydantic.BaseModel):
    """
    A class representing an event in a PostgreSQL channel.

    Attributes:
        channel: The PostgreSQL channel the event belongs to.
        operation: The type of operation performed (insert, update or delete).
        sent_at: The timestamp when the event was sent.
        table: The table the event is associated with.
        received_at: The timestamp when the event was received.
    """

    channel: PGChannel
    operation: OPERATIONS
    sent_at: pydantic.AwareDatetime
    table: str
    received_at: pydantic.AwareDatetime = pydantic.Field(
        init=False,
        default_factory=lambda: datetime.datetime.now(
            tz=datetime.timezone.utc,
        ),
    )

    @property
    def latency(self) -> datetime.timedelta:
        """
        Calculate the latency between when the event was sent and received.
        """
        return self.received_at - self.sent_at
