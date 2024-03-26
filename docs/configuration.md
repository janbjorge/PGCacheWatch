# Configuration
Configuring PGCacheWatch for optimal operation with PostgreSQL involves careful consideration of how you establish and manage your database connections, particularly when using asyncpg for asynchronous communication. Here's a refined approach to configuration, taking into account the nuances of connection pooling, listener persistence, and environmental configuration options.

### Using Connection Pools with PGCacheWatch

While asyncpg’s connection pooling is a powerful feature for managing database connections efficiently, it requires careful handling when used with LISTEN/NOTIFY channels due to the nature of persistent listeners.

#### Persistent Listeners
When a connection from the pool is used to set up LISTEN commands for notifications, it's important to keep that connection dedicated to listening. Returning the connection to the pool would remove the listeners, as the connection could be reused for other database operations, disrupting the notification flow.

#### Dedicated Listener Connection
To maintain persistent LISTEN operations, establish a dedicated connection outside the pool specifically for this purpose. This ensures that the NOTIFY listeners remain active throughout the application's lifecycle.

```python
# Dedicated listener connection
listener_conn = await asyncpg.connect(dsn="postgres://user:password@localhost/dbname")

# Connection pool for other database operations
pool = await asyncpg.create_pool(dsn="postgres://user:password@localhost/dbname")
```

### Best Practices for Configuration

- Security: Always use secure methods (like environment variables or secret management tools) to store and access database credentials, avoiding hard-coded values.
- Connection Pooling: Utilize connection pooling for handling database operations but maintain a separate, dedicated connection for LISTEN/NOTIFY to ensure continuous event listening.
- SSL Configuration: Enable SSL for database connections in production environments to secure data in transit. This can be configured via connection parameters or environment variables.
