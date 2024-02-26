# Examples

PGCacheWatch offers a versatile approach to leveraging PostgreSQL's NOTIFY/LISTEN capabilities for real-time event handling and cache invalidation in Python applications. Below are a few detailed examples of how PGCacheWatch can be integrated into different scenarios, providing solutions to common problems encountered in web development and data management.

## Automating User Data Enrichment

### Challenge
When new users register on a platform, it's common to need additional information that isn't immediately provided at the time of sign-up. Fetching and updating this information in real-time can enhance user profiles and improve the user experience.

### Approach
This example demonstrates using PGCacheWatch for real-time user data enrichment upon new registrations. By listening for new user events, the system can asynchronously fetch additional information from external services and update the user's profile without manual intervention.

```python
import asyncio
import asyncpg
from pgcachewatch import listeners, models

# Process new user events for data enrichment
async def process_new_user_event() -> None:
    ...


# Main listener function for new user events
async def listen_for_new_users() -> None:
    conn = await asyncpg.connect()
    listener = listeners.PGEventQueue()
    await listener.connect(conn)

    try:
        print("Listening for new user events...")
        while event := await listener.get():
            if event.operation == "insert":
                await process_new_user_event()
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(listen_for_new_users())
```

## Integrating with FastAPI

### Challenge
In web applications, ensuring data returned to the user is fresh and consistent with the database can be challenging, especially after updates. Traditional cache invalidation strategies often result in stale data or unnecessary database queries.

### Approach
This example shows how to integrate PGCacheWatch with FastAPI to dynamically invalidate cache following database changes. This ensures data freshness and consistency by invalidating the cache only when relevant database changes occur, thus optimizing performance and user experience.

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
    await listener.connect(conn)
    yield
    await conn.close()

APP = FastAPI(lifespan=app_setup_teardown)

@decorators.cache(strategy=strategies.Greedy(listener=listener, predicate=lambda x: x.operation == "update"))
async def cached_query(user_id: int) -> dict[str, str]:
    return {"data": "query result"}

@APP.get("/data")
async def get_data(user_id: int) -> dict:
    return await cached_query(user_id)
```