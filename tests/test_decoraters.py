import asyncio
import collections
import datetime

import pytest
from pgcachewatch import decorators, listeners, models, strategies


@pytest.mark.parametrize("N", (4, 16, 64, 512))
async def test_gready_cache_decorator(N: int) -> None:
    statistics = collections.Counter[str]()
    listener = await listeners.PGEventQueue.create(
        models.PGChannel("test_cache_decorator")
    )

    @decorators.cache(
        strategy=strategies.Gready(listener=listener),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def now() -> datetime.datetime:
        return datetime.datetime.now()

    await asyncio.gather(*[now() for _ in range(N)])
    assert statistics["hit"] == N - 1
    assert statistics["miss"] == 1

    assert listener._pgconn
    await listener._pgconn.close()
