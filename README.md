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

## Automating User Data Enrichment with PGCacheWatch and Asyncio

In the era of data-driven applications, keeping user information comprehensive and up-to-date is paramount. However, the challenge often lies in efficiently updating user profiles with additional information fetched from external sources, especially in response to new user registrations. This process can significantly benefit from automation, ensuring that every new user's data is enriched without manual intervention.

The following Python example leverages `PGCacheWatch` in conjunction with `asyncio` and `asyncpg` to automate the enrichment of new user data in a PostgreSQL database. By listening for new user events, the application fetches additional information asynchronously from simulated external REST APIs and updates the user's record. This seamless integration not only enhances data quality but also optimizes backend workflows by reducing the need for constant database polling.

### What This Example Covers

- **Listening for New User Registrations**: Utilizing `PGCacheWatch` to listen for new user events in a PostgreSQL database, triggering data enrichment processes.
- **Fetching Additional Information**: Simulating asynchronous calls to external REST APIs to fetch additional information for newly registered users.
- **Updating User Profiles**: Demonstrating how to update user records in the database with the fetched information, completing the data enrichment cycle.

This guide is intended for developers seeking to automate data enrichment processes in their applications, particularly those using PostgreSQL for data management. The example provides a practical approach to integrating real-time event handling with asynchronous programming for efficient data updates.

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

## Integrating PGCacheWatch with FastAPI for Dynamic Cache Invalidation
In modern web applications, maintaining data consistency while ensuring high performance can be a significant challenge. Caching is a common strategy to enhance performance, but it introduces complexity when it comes to invalidating cached data upon updates. `PGCacheWatch` offers a robust solution by leveraging PostgreSQL's NOTIFY/LISTEN features to invalidate cache entries in real-time, ensuring your application's data remains fresh and consistent.

This example demonstrates how to integrate `PGCacheWatch` with FastAPI, a popular asynchronous web framework, to create an efficient and responsive web application. By combining FastAPI's scalability with `PGCacheWatch`'s real-time cache invalidation capabilities, developers can build applications that automatically update cached data upon changes in the database, minimizing latency and improving user experience.

### What You'll Learn

- **Setting Up `PGCacheWatch` with FastAPI**: How to configure `PGCacheWatch` to work within the FastAPI application lifecycle, including database connection setup and teardown.
- **Implementing Cache Invalidation Strategies**: Utilizing `PGCacheWatch`'s decorators and strategies to invalidate cached data based on database events, specifically focusing on updates.
- **Creating Responsive Endpoints**: Building FastAPI routes that serve dynamically updated data, ensuring that the information presented to the user is always up-to-date.

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