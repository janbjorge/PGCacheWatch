import datetime
import typing

import pydantic

OPERATIONS = typing.Literal["insert", "update", "delete", "truncate"]
PGChannel = typing.NewType("PGChannel", str)


@typing.final
class Event(pydantic.BaseModel, frozen=True):
    """
    A class representing an event in a PostgreSQL channel.

    Attributes:
        channel: The PostgreSQL channel the event belongs to.
        operation: The type of operation performed (insert, update, delete or truncate).
        sent_at: The timestamp when the event was sent.
        table: The table the event is associated with.
        received_at: The timestamp when the event was received.
    """

    channel: PGChannel
    operation: OPERATIONS
    sent_at: datetime.datetime
    table: str
    received_at: datetime.datetime = pydantic.Field(
        default_factory=lambda: datetime.datetime.now(
            tz=datetime.timezone.utc,
        )
    )

    @property
    def latency(self) -> datetime.timedelta:
        """
        Calculate the latency between when the event was sent and received.
        """
        return self.received_at - self.sent_at
