import collections
import datetime
import typing

from . import listeners, models, utils


class Strategy(typing.Protocol):
    """
    A protocol defining the clear method for different strategies.
    """

    def clear(self) -> bool:
        raise NotImplementedError

    def pg_connection_healthy(self) -> bool:
        raise NotImplementedError


class Gready(Strategy):
    """
    A strategy that clears events based on a predicate until a deadline is reached.
    """

    def __init__(
        self,
        listener: listeners.PGEventQueue,
        deadline: models.DeadlineSetting = models.DeadlineSetting(),
        predicate: typing.Callable[[models.Event], bool] = bool,
    ) -> None:
        super().__init__()
        self._listener = listener
        self._predicate = predicate
        self._deadline = deadline

    def pg_connection_healthy(self) -> bool:
        return self._listener.pg_connection_healthy()

    def clear(self) -> bool:
        for event in utils.pick_until_deadline(
            self._listener,
            settings=self._deadline,
        ):
            if self._predicate(event):
                return True
        return False


class Windowed(Strategy):
    """
    A strategy that clears events when a specified sequence
    of operations occurs within a window.
    """

    def __init__(
        self,
        listener: listeners.PGEventQueue,
        window: list[models.OPERATIONS],
        deadline: models.DeadlineSetting = models.DeadlineSetting(),
    ) -> None:
        super().__init__()
        self._listener = listener
        self._window = window
        self._deadline = deadline
        self._events = collections.deque[models.OPERATIONS](maxlen=len(self._window))

    def pg_connection_healthy(self) -> bool:
        return self._listener.pg_connection_healthy()

    def clear(self) -> bool:
        for event in utils.pick_until_deadline(
            self._listener,
            settings=self._deadline,
        ):
            self._events.append(event.operation)
            if len(self._window) == len(self._events) and all(
                w == e for w, e in zip(self._window, self._events)
            ):
                return True
        return False


class Timed(Strategy):
    """
    A strategy that clears events based on a specified time interval between events.
    """

    def __init__(
        self,
        listener: listeners.PGEventQueue,
        timedelta: datetime.timedelta,
        deadline: models.DeadlineSetting = models.DeadlineSetting(),
    ) -> None:
        super().__init__()
        self._listener = listener
        self._timedelta = timedelta
        self._deadline = deadline
        self._previous = datetime.datetime.now(tz=datetime.timezone.utc)

    def pg_connection_healthy(self) -> bool:
        return self._listener.pg_connection_healthy()

    def clear(self) -> bool:
        for current in utils.pick_until_deadline(
            queue=self._listener,
            settings=self._deadline,
        ):
            if current.sent_at - self._previous > self._timedelta:
                self._previous = current.sent_at
                return True
        return False
