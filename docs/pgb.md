## PG-Bouncer Service

The new PG-Bouncer service, is designed to enhance PGCacheWatch by enabling efficient distribution of PostgreSQL notifications to multiple clients. This service acts as a middleware, receiving notifications from PostgreSQL and broadcasting them to connected clients via WebSockets. This "fan-out" effect ensures real-time cache invalidation across all clients with minimal database connections.

###  Key Benefits:

- **Scalability**: Handles numerous clients without increasing load on the PostgreSQL server.
- **Efficiency**: Reduces the need for multiple direct connections to PostgreSQL for NOTIFY/LISTEN.
- **Real-time**: Ensures immediate cache invalidation across services upon database changes.

### Illustration:

```
                                      +-------------------+
                                      |   PostgreSQL DB   |
                                      | - NOTIFY on event |
                                      +---------+---------+
                                                |
                                                | NOTIFY
                                                |
                                      +---------v---------+
                                      |  PG-Bouncer       |
                                      |  Service          |
                                      | - Fan-out NOTIFY  |
                                      +---------+---------+
                                                |
                                  +-------------+-------------+
                                  |                           |
                          +-------v-------+           +-------v-------+
                          | WebSocket     |           | WebSocket     |
                          | Client 1      |           | Client N      |
                          | - Invalidate  |           | - Invalidate  |
                          |   Cache       |           |   Cache       |
                          +---------------+           +---------------+
```

To leverage the PG-Bouncer service within your PGCacheWatch setup, ensure it's running and accessible by your application. Configure PGCacheWatch to connect to PG-Bouncer instead of directly to PostgreSQL for notifications. This setup amplifies the effectiveness of your cache invalidation strategy by ensuring timely updates across all client caches with optimized resource usage.

### Running the PG-Bouncer Service
To start the PG-Bouncer service, use the following command in your terminal. This command utilizes uvicorn, an ASGI server, to run the service defined in the `pgcachewatch.pg_bouncer:main` module. The --factory flag is used to indicate that uvicorn should call the provided application factory function to get the ASGI application instance.

```bash
uvicorn pgcachewatch.pg_bouncer:main --factory
```
