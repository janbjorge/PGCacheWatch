# Introduction

PGCacheWatch is a Python library designed to enhance applications by providing real-time PostgreSQL event notifications, facilitating efficient cache invalidation. It leverages PostgreSQL's existing NOTIFY/LISTEN infrastructure to simplify cache management, ensuring both high performance and data consistency. This document serves as an introduction to PGCacheWatch, covering key features, cache invalidation strategies, and the setup process.

## Interaction with PostgreSQL via LISTEN/NOTIFY

PGCacheWatch utilizes PostgreSQL's LISTEN/NOTIFY mechanism to receive real-time notifications of database changes, enabling applications to invalidate cached data promptly and efficiently. This process involves the following steps:

1. **Setting up NOTIFY triggers in PostgreSQL**: Triggers are configured on the database to emit NOTIFY signals upon specified events (e.g., insert, update, delete operations). These triggers call a function that issues the NOTIFY command with a payload containing event details.

2. **Listening for notifications in Python**: PGCacheWatch establishes a connection to PostgreSQL and listens on the specified channel(s) for notifications. This is achieved through the asyncpg library, allowing for asynchronous, non-blocking database communication.

3. **Processing received notifications**: Upon receiving a notification, PGCacheWatch parses the payload, constructs an event object, and enqueues it for processing. This mechanism enables the application to react to database changes in real-time, ensuring the cache remains up-to-date.

4. **Cache Invalidation Strategies**: Depending on the application's requirements, different strategies can be employed to invalidate the cache. These strategies (Greedy, Windowed, Timed) offer varying trade-offs between immediacy and performance, allowing developers to choose the most appropriate approach based on their specific needs.

## Example Usage

The following example demonstrates how to set up a PostgreSQL event queue in PGCacheWatch, connect to a PostgreSQL channel, and listen for events:

```python
import asyncio
import asyncpg

from pgcachewatch.listeners import PGEventQueue
from pgcachewatch.models import PGChannel

async def main():
    conn = await asyncpg.connect(dsn='postgres://user:password@localhost/dbname')
    event_queue = PGEventQueue()
    await event_queue.connect(conn)

    try:
        print('Listening for events...')
        while True:
            event = await event_queue.get()
            print(f'Received event: {event}')
    finally:
        await conn.close()

if __name__ == '__main__':
    asyncio.run(main())
```