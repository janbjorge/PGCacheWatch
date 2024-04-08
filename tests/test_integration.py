import asyncio
import collections
import datetime

import asyncpg
import pytest
from pgcachewatch import cli, decorators, listeners, strategies


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=datetime.timezone.utc)


async def test_1_install_triggers(
    monkeypatch: pytest.MonkeyPatch,
    pgconn: asyncpg.Connection,
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pgcachewatch", "install", "sysconf", "--commit"],
    )
    await cli.main()
    assert (
        len(
            await pgconn.fetch(
                cli.queries.fetch_trigger_names(cli.cliparser().trigger_name)
            )
        )
        == 3
    )


@pytest.mark.parametrize("N", (2, 8, 16))
async def test_2_caching(
    N: int,
    pgconn: asyncpg.Connection,
    pgpool: asyncpg.Pool,
) -> None:
    statistics = collections.Counter[str]()
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn)

    cnt = 0

    @decorators.cache(
        strategy=strategies.Greedy(listener=listener),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def fetch_sysconf() -> list:
        nonlocal cnt
        cnt += 1
        return await pgpool.fetch("SELECT * FROM sysconf")

    await asyncio.gather(*[fetch_sysconf() for _ in range(N)])

    # Give a bit of leeway due IO network io.
    await asyncio.sleep(0.1)

    assert cnt == 1
    assert statistics["miss"] == 1
    assert statistics["hit"] == N - 1


async def test_3_cache_invalidation_update(
    pgconn: asyncpg.Connection,
    pgpool: asyncpg.Pool,
) -> None:
    statistics = collections.Counter[str]()
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn)

    @decorators.cache(
        strategy=strategies.Greedy(listener=listener),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def fetch_sysconf() -> list:
        return await pgpool.fetch("SELECT * FROM sysconf")

    async def blast() -> list:
        before = await fetch_sysconf()
        while (rv := await fetch_sysconf()) == before:
            await asyncio.sleep(0.001)
        return rv

    blast_task = asyncio.create_task(blast())
    await pgpool.execute(
        "UPDATE sysconf set value = $1 where key = 'updated_at'",
        utcnow().isoformat(),
    )
    await asyncio.wait_for(blast_task, 1)
    # First fetch and update
    assert statistics["miss"] == 2


async def test_3_cache_invalidation_insert(
    pgconn: asyncpg.Connection,
    pgpool: asyncpg.Pool,
) -> None:
    statistics = collections.Counter[str]()
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn)

    @decorators.cache(
        strategy=strategies.Greedy(listener=listener),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def fetch_sysconf() -> list:
        return await pgpool.fetch("SELECT * FROM sysconf")

    async def blast() -> list:
        before = await fetch_sysconf()
        while (rv := await fetch_sysconf()) == before:
            await asyncio.sleep(0.001)
        return rv

    blast_task = asyncio.create_task(blast())
    await pgpool.execute(
        "INSERT INTO sysconf (key, value) VALUES ($1, $2);",
        utcnow().isoformat(),
        utcnow().isoformat(),
    )
    await asyncio.wait_for(blast_task, 1)
    # First fetch and insert
    assert statistics["miss"] == 2


async def test_3_cache_invalidation_delete(
    pgconn: asyncpg.Connection,
    pgpool: asyncpg.Pool,
) -> None:
    statistics = collections.Counter[str]()
    listener = listeners.PGEventQueue()
    await listener.connect(pgconn)

    @decorators.cache(
        strategy=strategies.Greedy(listener=listener),
        statistics_callback=lambda x: statistics.update([x]),
    )
    async def fetch_sysconf() -> list:
        return await pgpool.fetch("SELECT * FROM sysconf")

    async def blast() -> list:
        before = await fetch_sysconf()
        while (rv := await fetch_sysconf()) == before:
            await asyncio.sleep(0.001)
        return rv

    blast_task = asyncio.create_task(blast())
    await pgpool.execute(
        "DELETE FROM sysconf WHERE key ~ '^\\d{4}-\\d{2}-\\d{2}';",
    )
    await asyncio.wait_for(blast_task, 1)
    # First fetch and insert
    assert statistics["miss"] == 2


async def test_4_uninstall_triggers(
    monkeypatch: pytest.MonkeyPatch,
    pgconn: asyncpg.Connection,
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["pgcachewatch", "uninstall", "--commit"],
    )
    await cli.main()
    assert (
        len(
            await pgconn.fetch(
                cli.queries.fetch_trigger_names(cli.cliparser().trigger_name)
            )
        )
        == 0
    )
