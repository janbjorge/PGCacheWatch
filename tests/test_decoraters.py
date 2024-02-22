import asyncio
import collections
import datetime
from typing import NoReturn

import asyncpg
import pytest
from pgcachewatch import decorators, listeners, models, strategies


@pytest.mark.parametrize("N", (1, 2, 4, 16, 64))
async def test_greedy_cache_decorator(N: int, pgconn: asyncpg.Connection) -> None:
    statistics = collections.Counter[str]()
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn, models.PGChannel("test_cache_decorator"))

    @decorators.cache(
        strategy=strategies.Greedy(listener=listener),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def now() -> datetime.datetime:
        return datetime.datetime.now()

    nows = set(await asyncio.gather(*[now() for _ in range(N)]))
    assert len(nows) == 1

    assert statistics["hit"] == N - 1
    assert statistics["miss"] == 1


@pytest.mark.parametrize("N", (1, 2, 4, 16, 64))
async def test_greedy_cache_decorator_connection_closed(
    N: int,
    pgconn: asyncpg.Connection,
) -> None:
    listener = listeners.PGEventQueue()
    await listener.connect(
        pgconn,
        models.PGChannel("test_greedy_cache_decorator_connection_closed"),
    )
    await pgconn.close()

    @decorators.cache(strategy=strategies.Greedy(listener=listener))
    async def now() -> datetime.datetime:
        return datetime.datetime.now()

    nows = await asyncio.gather(*[now() for _ in range(N)])
    assert len(set(nows)) == N


@pytest.mark.parametrize("N", (1, 2, 4, 16, 64))
async def test_greedy_cache_decorator_exceptions(
    N: int,
    pgconn: asyncpg.Connection,
) -> None:
    listener = listeners.PGEventQueue()
    await listener.connect(
        pgconn,
        models.PGChannel("test_greedy_cache_decorator_exceptions"),
    )

    @decorators.cache(strategy=strategies.Greedy(listener=listener))
    async def raise_runtime_error() -> NoReturn:
        raise RuntimeError

    for _ in range(N):
        with pytest.raises(RuntimeError):
            await raise_runtime_error()

    exceptions = await asyncio.gather(
        *[raise_runtime_error() for _ in range(N)],
        return_exceptions=True,
    )
    assert len(exceptions) == N
    assert all(isinstance(exc, RuntimeError) for exc in exceptions)


@pytest.mark.parametrize("N", (1, 2, 4, 16, 64))
async def test_greedy_cache_identity(
    N: int,
    pgconn: asyncpg.Connection,
) -> None:
    statistics = collections.Counter[str]()
    listener = listeners.PGEventQueue()
    await listener.connect(
        pgconn,
        models.PGChannel("test_greedy_cache_decorator_exceptions"),
    )

    @decorators.cache(
        strategy=strategies.Greedy(listener=listener),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def identity(x: int) -> int:
        return x

    results = await asyncio.gather(*[identity(n) for n in range(N)])

    assert sorted(results) == list(range(N))
    assert statistics["miss"] == N
    assert statistics["hit"] == 0


@pytest.mark.parametrize("N", (1, 2, 4, 16, 64))
async def test_greedy_cache_sleepy(
    N: int,
    pgconn: asyncpg.Connection,
) -> None:
    statistics = collections.Counter[str]()
    listener = listeners.PGEventQueue()
    await listener.connect(
        pgconn,
        models.PGChannel("test_greedy_cache_decorator_exceptions"),
    )

    @decorators.cache(
        strategy=strategies.Greedy(listener=listener),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def now() -> datetime.datetime:
        await asyncio.sleep(0.01)
        return datetime.datetime.now()

    results = await asyncio.gather(*[now() for _ in range(N)])

    assert len(set(results)) == 1
    assert statistics["miss"] == 1
    assert statistics["hit"] == N - 1
