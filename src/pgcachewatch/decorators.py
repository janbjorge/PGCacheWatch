import asyncio
from functools import _make_key as make_key
from typing import Awaitable, Callable, Hashable, Literal, TypeVar

from typing_extensions import ParamSpec

from pgcachewatch import strategies
from pgcachewatch.logconfig import logger

P = ParamSpec("P")
T = TypeVar("T")


def cache(
    strategy: strategies.Strategy,
    statistics_callback: Callable[[Literal["hit", "miss"]], None] = lambda _: None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """
    Decorator for caching asynchronous function calls based on provided
    caching strategy.

    This decorator leverages an asynchronous caching strategy to manage cache
    entries and ensure efficient data retrieval. The cache is keyed by the
    function's arguments, with support for both positional and keyword arguments.
    It provides mechanisms for cache invalidation and supports concurrent access by
    utilizing asyncio.Future for pending results, effectively preventing cache
    stampedes.

    The decorator ensures that:
    - If the connection is unhealthy, caching is bypassed, and the
        function is executed directly.
    - The cache is cleared based on signals from the caching
        strategy, indicating data invalidation needs.
    - Cache entries are created or retrieved based on the unique call
        signature of the decorated function.
    - Cache hits and misses are logged and can trigger custom actions
        via the statistics_callback.

    Note: This decorator is intended for use with asynchronous functions.
    """

    def outer(fn: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        cached = dict[Hashable, asyncio.Future[T]]()

        async def inner(*args: P.args, **kwargs: P.kwargs) -> T:
            # If db-conn is down, disable cache.
            if not strategy.connection_healthy():
                logger.critical("Database connection is closed, caching disabled.")
                return await fn(*args, **kwargs)

            # Clear cache if we have a event from
            # the database the instructs us to clear.
            if strategy.clear():
                logger.debug("Cache clear")
                cached.clear()

            key = make_key(args, kwargs, typed=False)

            try:
                waiter = cached[key]
            except KeyError:
                # Cache miss
                logger.debug("Cache miss")
                statistics_callback("miss")
            else:
                # Cache hit
                logger.debug("Cache hit")
                statistics_callback("hit")
                return await waiter

            # Initialize Future to prevent cache stampedes.
            cached[key] = waiter = asyncio.Future[T]()

            try:
                # # Attempt to compute result and set for waiter
                waiter.set_result(await fn(*args, **kwargs))
            except Exception as e:
                # Remove key from cache on failure.
                cached.pop(key, None)
                # Propagate exception to all awaiting the future.
                waiter.set_exception(e)

            return await waiter

        return inner

    return outer
