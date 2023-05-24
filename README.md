## PG-Notefier
This is a pet project that I've been working on for a few hours, the basic idea is to use Postgres pub/sub-system to invalidate cached in Python. By either adding a trigger to a table or emitting events. The main idea is that most stacks(in my case) will have Postgres running, and instead of installing and dealing with Reddis or other memory options, this feels like a very cheap option. The system runs a small WebSocket server that acts as a bouncer to protect Postgres from connection bloat.

**This is just pet project!**

## Setup

If you got an Postgres instance running, you can just run set the _asyncpg_ environment variables in order to let the service connect to your database. You have to provide an _channel_ as well.

Exmaple:
```bash
python3 -m server --channel table_changes
```