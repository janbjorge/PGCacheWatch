# PGCacheWatch
[![CI](https://github.com/janbjorge/PGCacheWatch/actions/workflows/ci.yml/badge.svg)](https://github.com/janbjorge/PGCacheWatch/actions/workflows/ci.yml?query=branch%3Amain)
[![pypi](https://img.shields.io/pypi/v/PGCacheWatch.svg)](https://pypi.python.org/pypi/PGCacheWatch)
[![downloads](https://static.pepy.tech/badge/PGCacheWatch/month)](https://pepy.tech/project/PGCacheWatch)
[![versions](https://img.shields.io/pypi/pyversions/PGCacheWatch.svg)](https://github.com/janbjorge/PGCacheWatch)

PGCacheWatch is a Python library crafted to empower applications with real-time PostgreSQL event notifications for efficient cache invalidation, directly leveraging existing PostgreSQL infrastructure. This approach eliminates the need for additional technologies for cache management, simplifying your stack while enhancing performance and real-time data consistency.

## Key Advantages
- **Leverage Existing Infrastructure**: Utilizes PostgreSQL's native NOTIFY/LISTEN capabilities for event-driven cache invalidation, avoiding the overhead of integrating external caching systems.
- **Asynchronous and Efficient**: Built on top of `asyncpg` for asynchronous database communication, ensuring non-blocking I/O operations and optimal performance.
- **Flexible Cache Invalidation Strategies**: Offers a variety of strategies (e.g., Greedy, Windowed, Timed) for nuanced cache invalidation control, tailored to different application needs.
- **Simple Yet Powerful API**: Designed with simplicity in mind, offering a straightforward setup process and an intuitive API for managing cache invalidation logic.

## Installation
To install PGCacheWatch, run the following command in your terminal:
```bash
pip install pgcachewatch
```

## Using PGCacheWatch
### Setting Up
Initialize PostgreSQL triggers to emit NOTIFY events on data changes. PGCacheWatch provides utility scripts for easy trigger setup
```bash
pgcachewatch install <tables-to-cache>
```

### FastAPI Example
Example showing how to use PGCacheWatch for cache invalidation in a FastAPI app

```python
import contextlib
import typing

import asyncpg
from fastapi import FastAPI
from pgcachewatch import decorators, listeners, models, strategies

listener = listeners.PGEventQueue()


@contextlib.asynccontextmanager
async def app_setup_teardown(_: FastAPI) -> typing.AsyncGenerator[None, None]:
    conn = await asyncpg.connect()
    await listener.connect(conn, models.PGChannel("ch_pgcachewatch_table_change"))
    yield
    await conn.close()


APP = FastAPI(lifespan=app_setup_teardown)


# Only allow for cache refresh after an update
@decorators.cache(
    strategy=strategies.Gready(
        listener=listener,
        predicate=lambda x: x.operation == "update",
    )
)
async def cached_query() -> dict[str, str]:
    # Simulate a database query
    return {"data": "query result"}


@APP.get("/data")
async def get_data() -> dict:
    return await cached_query()
```
