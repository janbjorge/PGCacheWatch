##  🚀 PGCacheWatch - Supercharge Your Caching Strategy 🚀
[![CI](https://github.com/janbjorge/PGCacheWatch/actions/workflows/ci.yml/badge.svg)](https://github.com/janbjorge/PGCacheWatch/actions/workflows/ci.yml?query=branch%3Amain)
[![pypi](https://img.shields.io/pypi/v/PGCacheWatch.svg)](https://pypi.python.org/pypi/PGCacheWatch)
[![downloads](https://static.pepy.tech/badge/PGCacheWatch/month)](https://pepy.tech/project/PGCacheWatch)
[![versions](https://img.shields.io/pypi/pyversions/PGCacheWatch.svg)](https://github.com/janbjorge/PGCacheWatch)

---
📚 **Documentation**: [Explore the Docs 📖](https://pgcachewatch.readthedocs.io/en/latest/)

🔍 **Source Code**: [View on GitHub 💾](https://github.com/janbjorge/PGCacheWatch/)

---
PGCacheWatch is the a Python library designed to propel your applications into a new realm of efficiency with real-time PostgreSQL event notifications for cache invalidation. Wave goodbye to stale data and hello to seamless cache management, bolstered performance powered by the robust backbone of PostgreSQL.

## Example with FastAPI
PGCacheWatch integrates with FastAPI, empowering you to keep your application's data fresh and consistent by dynamically invalidating cache in line with database updates.

```python
import contextlib
import typing

import asyncpg
from fastapi import FastAPI
from pgcachewatch import decorators, listeners, models, strategies

# Initialize a PGEventQueue listener to listen for database events.
listener = listeners.PGEventQueue()

@contextlib.asynccontextmanager
async def app_setup_teardown(_: FastAPI) -> typing.AsyncGenerator[None, None]:
    """
    Asynchronous context manager for FastAPI app setup and teardown.

    This context manager is used to establish and close the database connection
    at the start and end of the FastAPI application lifecycle, respectively.
    """
    # Establish a database connection using asyncpg.
    conn = await asyncpg.connect()
    # Connect the listener to the database using the specified channel.
    await listener.connect(conn)
    yield  # Yield control back to the event loop.
    await conn.close()  # Ensure the database connection is closed on app teardown.

# Create an instance of FastAPI, specifying the app setup and teardown actions.
APP = FastAPI(lifespan=app_setup_teardown)

# Decorate the cached_query function with cache invalidation logic.
@decorators.cache(
    strategy=strategies.Greedy(
        listener=listener,
        # Invalidate the cache only for 'update' operations on the database.
        predicate=lambda x: x.operation == "update",
    )
)
async def cached_query(user_id: int) -> dict[str, str]:
    """
    Simulates a database query that benefits from cache invalidation.

    This function is decorated to use PGCacheWatch's cache invalidation, ensuring
    that the data returned is up-to-date following any relevant 'update' operations
    on the database.
    """
    # Return a mock data response.
    return {"data": "query result"}

# Define a FastAPI route to fetch data, utilizing the cached_query function.
@APP.get("/data")
async def get_data(user_id: int) -> dict:
    """
    This endpoint uses the cached_query function to return data, demonstrating
    how cache invalidation can be integrated into a web application route.
    """
    # Fetch and return the data using the cached query function.
    return await cached_query(user_id)
```
