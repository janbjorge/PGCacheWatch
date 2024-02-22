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

    def connection_healthy(self) -> bool:
        raise NotImplementedError


class Greedy(Strategy):
    """
    A strategy that clears events based on a predicate until a deadline is reached.
    """

    def __init__(
        self,
        listener: listeners.EventQueueProtocol,
        settings: models.DeadlineSetting = models.DeadlineSetting(),
        predicate: typing.Callable[[models.Event], bool] = bool,
    ) -> None:
        super().__init__()
        self._listener = listener
        self._predicate = predicate
        self._settings = settings

    def connection_healthy(self) -> bool:
        return self._listener.connection_healthy()

    def clear(self) -> bool:
        for current in utils.pick_until_deadline(
            self._listener,
            settings=self._settings,
        ):
            if self._predicate(current):
                return True
        return False


class Windowed(Strategy):
    """
    A strategy that clears events when a specified sequence
    of operations occurs within a window.
    """

    def __init__(
        self,
        listener: listeners.EventQueueProtocol,
        window: list[models.OPERATIONS],
        settings: models.DeadlineSetting = models.DeadlineSetting(),
    ) -> None:
        super().__init__()
        self._listener = listener
        self._window = window
        self._settings = settings
        self._events = collections.deque[models.OPERATIONS](maxlen=len(self._window))

    def connection_healthy(self) -> bool:
        return self._listener.connection_healthy()

    def clear(self) -> bool:
        for current in utils.pick_until_deadline(
            self._listener,
            settings=self._settings,
        ):
            self._events.append(current.operation)
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
        listener: listeners.EventQueueProtocol,
        timedelta: datetime.timedelta,
        settings: models.DeadlineSetting = models.DeadlineSetting(),
    ) -> None:
        super().__init__()
        self._listener = listener
        self._timedelta = timedelta
        self._settings = settings
        self._previous = datetime.datetime.now(tz=datetime.timezone.utc)

    def connection_healthy(self) -> bool:
        return self._listener.connection_healthy()

    def clear(self) -> bool:
        for current in utils.pick_until_deadline(
            queue=self._listener,
            settings=self._settings,
        ):
            if current.sent_at - self._previous > self._timedelta:
                self._previous = current.sent_at
                return True
        return False
