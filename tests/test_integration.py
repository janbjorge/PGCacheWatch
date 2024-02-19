import asyncio
import collections

import asyncpg
import pytest
from pgcachewatch import cli, decorators, listeners, models, strategies


async def test_1_install_triggers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pgcachewatch", "install", "sysconf", "--commit"],
    )
    await cli.main()


@pytest.mark.parametrize("N", (2, 8, 16))
async def test_2_caching(
    N: int,
    pgconn: asyncpg.Connection,
    pgpool: asyncpg.Pool,
) -> None:
    statistics = collections.Counter[str]()
    listener = await listeners.PGEventQueue.create(
        models.PGChannel("test_2_caching"),
        pgconn=pgconn,
    )

    cnt = 0

    @decorators.cache(
        strategy=strategies.Gready(listener=listener),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def fetch_sysconf() -> list:
        nonlocal cnt
        cnt += 1
        return await pgpool.fetch("SELECT * FROM sysconf")

    await asyncio.gather(*[fetch_sysconf() for _ in range(N)])
    assert cnt == 1
    assert statistics["miss"] == 1
    assert statistics["hit"] == N - 1


async def test_3_uninstall_triggers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pgcachewatch", "uninstall", "--commit"],
    )
    await cli.main()
