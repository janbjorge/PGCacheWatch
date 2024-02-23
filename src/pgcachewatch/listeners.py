import asyncio
import datetime
import json
from typing import Protocol

import asyncpg

from . import models
from .logconfig import logger


def _critical_termination_listener(*_: object, **__: object) -> None:
    # Must be defined in the global namespace, as ayncpg keeps
    # a set of functions to call. This this will now happen once as
    # all instance will point to the same function.
    logger.critical("Connection is closed / terminated.")


class EventQueueProtocol(Protocol):
    """
    Protocol for an event queue interface.

    Specifies the required methods for an event queue to check the connection health
    and to retrieve events without waiting. Implementing classes must provide concrete
    implementations of these methods to ensure compatibility with the event handling
    system.
    """

    def connection_healthy(self) -> bool:
        """
        Checks if the connection is healthy.

        This method should return True if the connection to the underlying service
        (e.g., database, message broker) is active and healthy, False otherwise.

        Returns:
            bool: True if the connection is healthy, False otherwise.
        """
        raise NotImplementedError

    def get_nowait(self) -> models.Event:
        """
        Retrieves an event from the queue without waiting.

        Attempts to immediately retrieve an event from the queue. If no event is
        available, this method should raise an appropriate exception (e.g., QueueEmpty).

        Returns:
            models.Event: The event retrieved from the queue.

        Raises:
            QueueEmpty: If no event is available in the queue to retrieve.
        """
        raise NotImplementedError


class PGEventQueue(asyncio.Queue[models.Event]):
    """
    A PostgreSQL event queue that listens to a specified
    channel and stores incoming events.
    """

    def __init__(
        self,
        max_size: int = 0,
        max_latency: datetime.timedelta = datetime.timedelta(milliseconds=500),
    ) -> None:
        super().__init__(maxsize=max_size)
        self._pg_channel: None | models.PGChannel = None
        self._pg_connection: None | asyncpg.Connection = None
        self._max_latency = max_latency

    async def connect(
        self,
        connection: asyncpg.Connection,
        channel: models.PGChannel = models.PGChannel("ch_pgcachewatch_table_change"),
    ) -> None:
        """
        Asynchronously connects the PGEventQueue to a specified
        PostgreSQL channel and connection.

        This method establishes a listener on a PostgreSQL channel
        using the provided connection. It is designed to be called
        once per PGEventQueue instance to ensure a one-to-one relationship
        between the event queue and a database channel. If an attempt is
        made to connect a PGEventQueue instance to more than one channel
        or connection, a RuntimeError is raised to enforce this constraint.

        Parameters:
        - connection: asyncpg.Connection
            The asyncpg connection object to be used for listening to database events.
        - channel: models.PGChannel
            The database channel to listen on for events.

        Raises:
        - RuntimeError: If the PGEventQueue is already connected to a
        channel or connection.

        Usage:
        ```python
        await pg_event_queue.connect(
            connection=your_asyncpg_connection,
            channel=your_pg_channel,
        )
        ```
        """
        if self._pg_channel or self._pg_connection:
            raise RuntimeError(
                "PGEventQueue instance is already connected to a channel and/or "
                "connection. Only supports one channel and connection per "
                "PGEventQueue instance."
            )

        self._pg_channel = channel
        self._pg_connection = connection
        self._pg_connection.add_termination_listener(_critical_termination_listener)
        await self._pg_connection.add_listener(self._pg_channel, self.parse_and_put)  # type: ignore[arg-type]

    def parse_and_put(
        self,
        connection: asyncpg.Connection,
        pid: int,
        channel: str,
        payload: str,
    ) -> None:
        """
        Parses a given payload and puts it into a queue. If the latency requirement is
        not met, logs a warning but still adds the event to the queue.
        If parsing or queuing fails, logs the exception.
        """
        try:
            parsed = models.Event.model_validate(
                json.loads(payload) | {"channel": channel}
            )
        except Exception:
            logger.exception("Unable to parse `%s`.", payload)
        else:
            if parsed.latency > self._max_latency:
                logger.warning("Latency for %s above %s.", parsed, self._max_latency)
            logger.info("Received event: %s on %s", parsed, channel)
            try:
                self.put_nowait(parsed)
            except Exception:
                logger.exception("Unable to queue `%s`.", parsed)

    def connection_healthy(self) -> bool:
        return bool(self._pg_connection and not self._pg_connection.is_closed())
