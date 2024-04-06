"""
Facilitates WebSocket clients subscribing to PostgreSQL notifications via
a single connection. Reduces PostgreSQL server load by sharing one connection
among multiple clients

Usage example:
`uvicorn pgcachewatch.pg_bouncer:main --factory`
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg
from fastapi import Depends, FastAPI, Response, WebSocket, WebSocketDisconnect


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manages the applications database conncetion.
    """
    app.state.pg_connection = conn = await asyncpg.connect()
    try:
        yield
    finally:
        await conn.close()


def get_pg_connection(req: WebSocket) -> asyncpg.Connection:
    """
    Retrieves PostgreSQL connection from app state for FastAPI endpoints.
    """
    assert isinstance(
        conn := req.app.state.pg_connection,
        asyncpg.Connection,
    )
    return conn


def main() -> FastAPI:
    """
    Configures FastAPI app with PostgreSQL connection and WebSocket
    endpoint for PUB/SUB.
    """

    app = FastAPI(lifespan=lifespan)

    @app.get("/up")
    async def up() -> Response:
        return Response()

    @app.websocket("/pgpubsub/{channel}")
    async def pubsub_proxy(
        websocket: WebSocket,
        channel: str,
        conn: asyncpg.Connection = Depends(get_pg_connection),
    ) -> None:
        """
        Forwards messages from a PostgreSQL channel to WebSocket clients.
        """

        await websocket.accept()
        que = asyncio.Queue[str]()

        async def putter(
            connection: asyncpg.Connection,
            pid: int,
            channel: str,
            payload: str,
        ) -> None:
            """
            Enqueues message payloads for forwarding to WebSocket clients on new
            publication.
            """
            await que.put(payload)

        await conn.add_listener(channel, putter)  # type: ignore[arg-type]

        try:
            while True:
                await websocket.send_text(await que.get())
        except WebSocketDisconnect:
            await conn.remove_listener(channel, putter)  # type: ignore[arg-type]

    return app
