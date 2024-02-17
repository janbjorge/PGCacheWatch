import collections
import datetime

import pytest
from pgnotefi import decorators, listeners, models, strategies


@pytest.mark.asyncio
@pytest.mark.parametrize("N", (4, 16, 64))
async def test_cache_decorator(N: int) -> None:
    statistics = collections.Counter[str]()

    @decorators.cache(
        strategy=strategies.Gready(
            listener=await listeners.PGEventQueue.create(
                models.PGChannel("test_cache_decorator")
            )
        ),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def now() -> datetime.datetime:
        return datetime.datetime.now()

    for _ in range(N):
        await now()

    print(statistics, N)
    assert statistics["hit"] == N - 1
    assert statistics["miss"] == 1
