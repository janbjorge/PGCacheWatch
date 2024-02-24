# PGCacheWatch
[![CI](https://github.com/janbjorge/PGCacheWatch/actions/workflows/ci.yml/badge.svg)](https://github.com/janbjorge/PGCacheWatch/actions/workflows/ci.yml?query=branch%3Amain)
[![pypi](https://img.shields.io/pypi/v/PGCacheWatch.svg)](https://pypi.python.org/pypi/PGCacheWatch)
[![downloads](https://static.pepy.tech/badge/PGCacheWatch/month)](https://pepy.tech/project/PGCacheWatch)
[![versions](https://img.shields.io/pypi/pyversions/PGCacheWatch.svg)](https://github.com/janbjorge/PGCacheWatch)

PGCacheWatch is a Python library that enhances applications with real-time PostgreSQL event notifications, enabling efficient cache invalidation. It leverages the existing PostgreSQL infrastructure to simplify cache management while ensuring performance and data consistency.

## Key Features
- Real-Time Notifications: Utilize PostgreSQL's NOTIFY/LISTEN for immediate cache updates.
- Asynchronous Operations: Built on asyncpg for non-blocking database communication.
- Flexible Invalidation Strategies: Offers strategies like Greedy, Windowed, Timed for precise control.
- Easy Integration: Simple setup with an intuitive API for managing cache logic.

## Cache Invalidation Strategies
PGCacheWatch supports multiple strategies for cache invalidation, designed to suit various application needs.

- **Greedy**: Instantly invalidates cache on any related database change. Ideal for applications requiring the utmost data freshness.
- **Windowed**: Aggregates database changes over a set period or event count before invalidating the cache. This strategy strikes a balance between performance and data freshness, suitable for applications where slight data staleness is acceptable.
- **Timed**: Invalidates cache at fixed time intervals, regardless of database activity. Best for applications with predictable data access patterns, optimizing cache management while accommodating minor delays in data updates.

Selecting the right strategy depends on your specific requirements for data freshness and system performance.

## CLI Tool for NOTIFY Triggers

PGCacheWatch includes a Command Line Interface (CLI) tool designed to streamline the setup of NOTIFY triggers and functions within your PostgreSQL database:

- **CLI Tool**: Simplifies the creation and management of triggers and functions for the LISTEN/NOTIFY mechanism. This tool abstracts the complexity of script management, facilitating the integration of PGCacheWatch.
- **Notify Triggers and Functions**: The CLI automates the application of PostgreSQL functions and triggers that emit NOTIFY signals for specified database events. This ensures PGCacheWatch is promptly informed of changes impacting the cache.
- **Usage**: Executing a command such as `pgcachewatch install <tables-to-cache>` installs all necessary components to begin listening for database modifications and efficiently manage cache invalidation.
- **Advantages**: Leveraging the CLI tool enables developers to quickly deploy real-time cache invalidation capabilities in their applications, bypassing the intricacies of manual PostgreSQL configuration. This approach not only conserves development resources but also minimizes the risk of setup errors.

The CLI tool offers a straightforward method for implementing robust cache invalidation logic, capitalizing on the advanced features of PostgreSQL's NOTIFY/LISTEN without the need for extensive configuration.

## Installation
To install PGCacheWatch, run the following command in your terminal:
```bash
pip install pgcachewatch
```

## Setting Up
Install PGCacheWatch and initialize PostgreSQL triggers to emit NOTIFY events on data changes.
```bash
pgcachewatch install <tables-to-cache>
```

## Automating User Data Enrichment
This example demonstrates how to use PGCacheWatch with asyncio and asyncpg for real-time user data enrichment upon new registrations.

```python
import asyncio
import asyncpg
from pgcachewatch import listeners, models

async def fetch_users_without_additional_user_info() -> list:
    """
    Fetches a list of users who do not yet have additional user information associated.
    """
    ...

async def update_users_without_additional_user_info(
    user_id: int,
    additional_user_info: dict,
) -> None:
    """
    Updates users with the additional information fetched from an external source.
    """
    ...

async def fetch_additional_user_info(user_id: int) -> dict:
    """
    Simulates fetching additional user information via REST APIs.
    Note: This is a mock function. In a real application, this would make an asynchronous
    API call to fetch information from an external service.
    """
    await asyncio.sleep(1)  # Simulate API call delay
    return {"info": "Additional info for user"}  # Example return value

async def process_new_user_event() -> None:
    """
    Processes new user events by fetching additional information for new users
    and updating their records.
    """
    new_users = await fetch_users_without_additional_user_info()
    for user_id in new_users:
        user_info = await fetch_additional_user_info(user_id)
        await update_users_without_additional_user_info(user_id, user_info)

async def listen_for_new_users() -> None:
    """
    Listens for new user events and processes each event as it arrives.
    
    This function establishes a connection to the database and listens on a specified
    channel for new user events. When a new user is added (detected via an "insert" operation),
    it triggers the processing of new user events to fetch and update additional information.
    """
    conn = await asyncpg.connect()  # Connect to your PostgreSQL database
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

## Integrating PGCacheWatch with FastAPI
This example illustrates the integration of PGCacheWatch with FastAPI to dynamically invalidate cache following database changes, thus maintaining the freshness and consistency of your application's data.

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
async def cached_query() -> dict[str, str]:
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
async def get_data() -> dict:
    """
    This endpoint uses the cached_query function to return data, demonstrating
    how cache invalidation can be integrated into a web application route.
    """
    # Fetch and return the data using the cached query function.
    return await cached_query()
```