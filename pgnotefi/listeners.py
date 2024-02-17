import asyncio
import datetime
import json
import logging

import asyncpg
import pydantic

from . import env, listeners, models


def _critical_termination_listener():
    # Must be defined in the global namespace, as ayncpg keeps
    # a set of functions to call. This this will now happen once as
    # all instance will point to the same function.
    logging.critical("Connection is closed / terminated!")


class PGEventQueue(asyncio.Queue[models.Event]):
    """
    A PostgreSQL event queue that listens to a specified
    channel and stores incoming events.
    """

    def __init__(
        self,
        pgchannel: models.PGChannel,
        pgconn: asyncpg.Connection | None = None,
        dsn: pydantic.PostgresDsn | None = env.parsed.dsn,
        max_size: int = 0,
        max_latency: datetime.timedelta = datetime.timedelta(milliseconds=500),
        _called_by_create: bool = False,
    ) -> None:
        """
        Initializes the PGEventQueue instance. Use the create() classmethod to
        instantiate.
        """
        if not _called_by_create:
            raise RuntimeError(
                "Use classmethod create(...) to instantiate PGEventQueue."
            )
        super().__init__(maxsize=max_size)
        self._pgchannel = pgchannel
        self._pgconn = pgconn
        self._dsn = dsn
        self._max_latency = max_latency

    @classmethod
    async def create(
        cls,
        pgchannel: models.PGChannel,
        pgconn: asyncpg.Connection | None = None,
        dsn: pydantic.PostgresDsn | None = env.parsed.dsn,
        maxsize: int = 0,
        max_latency: datetime.timedelta = datetime.timedelta(milliseconds=500),
    ) -> listeners.PGEventQueue:
        """
        Creates and initializes a new PGEventQueue instance, connecting to the specified
        PostgreSQL channel. Returns the initialized PGEventQueue instance.
        """
        me = cls(
            pgchannel=pgchannel,
            pgconn=pgconn,
            dsn=dsn,
            max_size=maxsize,
            max_latency=max_latency,
            _called_by_create=True,
        )
        if me._pgconn is None:
            me._pgconn = pgconn or await asyncpg.connect(dsn=me._dsn)

        me._pgconn.add_termination_listener(_critical_termination_listener)
        await me._pgconn.add_listener(me._pgchannel, me.parse_and_put)

        return me

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
            if parsed.latency > self._max_latency:
                logging.warning("Latency for %s above %s.", parsed, self._max_latency)
        except Exception:
            logging.exception("Unable to parse `%s`.", payload)
        else:
            try:
                self.put_nowait(parsed)
            except Exception:
                logging.exception("Unable to queue `%s`.", parsed)

    def pg_connection_healthy(self) -> bool:
        return bool(self._pgconn and not self._pgconn.is_closed())
