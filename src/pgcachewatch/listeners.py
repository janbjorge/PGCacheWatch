import asyncio
import datetime
import json
from typing import Callable, Protocol

import asyncpg
import websockets

from . import models
from .logconfig import logger


def _critical_termination_listener(*_: object, **__: object) -> None:
    # Must be defined in the global namespace, as ayncpg keeps
    # a set of functions to call. This this will now happen once as
    # all instance will point to the same function.
    logger.critical("Connection is closed / terminated.")


def create_event_inserter(
    queue: asyncio.Queue[models.Event],
    max_latency: datetime.timedelta,
) -> Callable[
    [
        models.PGChannel,
        str | bytes | bytearray,
    ],
    None,
]:
    """
    Creates a callable that parses JSON payloads into `models.Event`
    objects and inserts them into a queue. If the event's latency
    exceeds the specified maximum, it logs a warning. Errors during
    parsing or inserting are logged as exceptions.
    """

    def parse_and_insert(
        channel: models.PGChannel,
        payload: str | bytes | bytearray,
    ) -> None:
        """
        Parses a JSON payload and inserts it into the queue as an `models.Event` object.
        """
        try:
            event_data = json.loads(payload)

            # Add or overwrite channel key with the current channel
            event_data["channel"] = channel

            parsed_event = models.Event.model_validate(event_data)

        except Exception:
            logger.exception(
                "Failed to parse payload: `%s`.",
                payload,
            )
            return

        if parsed_event.latency > max_latency:
            logger.warning(
                "Event latency (%s) exceeds maximum (%s): `%s` from `%s`.",
                parsed_event.latency,
                max_latency,
                parsed_event,
                channel,
            )
        else:
            logger.info(
                "Inserting event into queue: `%s` from `%s`.",
                parsed_event,
                channel,
            )

        try:
            queue.put_nowait(parsed_event)
        except Exception:
            logger.exception(
                "Unexpected error inserting event into queue: `%s`.",
                parsed_event,
            )

    return parse_and_insert


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

        event_handler = create_event_inserter(self, self._max_latency)
        await self._pg_connection.add_listener(
            self._pg_channel,
            lambda *x: event_handler(self._pg_channel, x[-1]),
        )

    def connection_healthy(self) -> bool:
        return bool(self._pg_connection and not self._pg_connection.is_closed())


class WSEventQueue(asyncio.Queue[models.Event]):
    def __init__(
        self,
        max_size: int = 0,
        max_latency: datetime.timedelta = datetime.timedelta(milliseconds=500),
    ) -> None:
        super().__init__(maxsize=max_size)
        self._max_latency = max_latency
        self._handler_task: asyncio.Task | None = None
        self._ws: websockets.WebSocketClientProtocol | None = None

    async def connect(
        self,
        ws: websockets.WebSocketClientProtocol,
        channel: models.PGChannel = models.PGChannel("ch_pgcachewatch_table_change"),
    ) -> None:
        async def _handler(ws: websockets.WebSocketClientProtocol) -> None:
            event_handler = create_event_inserter(self, self._max_latency)
            while True:
                try:
                    event_handler(self._pg_channel, await ws.recv())
                except websockets.ConnectionClosedOK:
                    break

        if self._handler_task is not None:
            raise RuntimeError(
                "WSEventQueue instance is already connected to a channel and/or "
                "connection. Only supports one channel and connection per "
                "WSEventQueue instance."
            )

        self._ws = ws
        self._pg_channel = channel
        self._handler_task = asyncio.create_task(_handler(ws))
        self._handler_task.add_done_callback(_critical_termination_listener)

    def connection_healthy(self) -> bool:
        task_ok = bool(self._handler_task and not self._handler_task.done())
        ws_ok = bool(self._ws and not self._ws.closed)
        return task_ok and ws_ok
