import asyncio
from typing import Awaitable, Callable, Hashable, Literal, TypeVar

from typing_extensions import ParamSpec

from pgcachewatch import strategies, utils
from pgcachewatch.logconfig import logger

P = ParamSpec("P")
T = TypeVar("T")


def cache(
    strategy: strategies.Strategy,
    statistics_callback: Callable[[Literal["hit", "miss"]], None] | None = None,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
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

            key = utils.make_key(args, kwargs)

            try:
                waiter = cached[key]
            except KeyError:
                # Cache miss
                ...
            else:
                # Cache hit
                logger.debug("Cache hit")
                if statistics_callback:
                    statistics_callback("hit")
                return await waiter

            logger.debug("Cache miss")
            if statistics_callback:
                statistics_callback("miss")

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
