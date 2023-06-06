#!/usr/bin/env python3

import asyncio
import json
import logging
import os
import pendulum
import queue
import websockets

from jtop.core.tegrastats import Tegrastats
from typing import Dict


DEFAULT_LOG_LEVEL: str = "INFO"
DEFAULT_BINARY: str = "/usr/bin/tegrastats"
DEFAULT_HOST: str = "0.0.0.0"
DEFAULT_PORT: int = 8888
DEFAULT_INTERVAL: float = 0.5

logging.basicConfig(
    level=(os.getenv("TEGRASTATS_LOG_LEVEL") or DEFAULT_LOG_LEVEL).upper()
)


INTERVAL: float = float(os.getenv("TEGRASTATS_INTERVAL") or DEFAULT_INTERVAL)
BINARY: str = os.getenv("TEGRASTATS_BINARY") or DEFAULT_BINARY

logging.debug(f"INTERVAL={INTERVAL}")
logging.debug(f"BINARY={BINARY}")

CONNECTIONS = set()
Q = queue.Queue()


def handle_stats(stats: Dict):
    """Enqueues the stats from the binary.

    A separate thread is used to read the output from the stats binary, which is
    typically the `/usr/bin/tegrastats` executable. The output is parsed and
    passed to this callback in a separate thread, but it needs to be sent to the
    websocket (main) thread. A synchronous, thread-safe queue is used to pass
    the stats dict from the parsing thread to the websocket (main) thread.
    """

    logging.debug(f"stats={stats}")
    # The Tegrastats parser from the jetson-stats package strips the date and
    # time. Plus, the date and time from the tegrastats binary only has second
    # resolution.
    stats["time"] = pendulum.now().format("YYYY-MM-DDTHH:mm:ss.SSSZ")
    Q.put(stats)


async def register(websocket):
    """Adds a client.

    Maintains the websocket clients that will receive the stats JSON.
    """

    CONNECTIONS.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        CONNECTIONS.remove(websocket)


async def broadcast_stats():
    """Broadcasts the stats to all connected clients.

    This dequeues stats from the thread-safe queue that were enqueued from the
    parsing thread. The stats dict is converted to JSON and broadcast to all
    connected websocket clients.
    """

    while True:
        try:
            stats = Q.get_nowait()
            websockets.broadcast(CONNECTIONS, json.dumps(stats))
        except queue.Empty:
            # A sleep is needed to yield the asyncio event loop to other tasks.
            # A tenth of the parsing interval is used as a "good enough" wait
            # because this "loop" should be faster than the parsing thread to
            # avoid backpressure in the queue.
            await asyncio.sleep(INTERVAL / 10.0)


async def main():
    """Starts the parsing thread and runs the websocket server."""

    tegrastats = Tegrastats(handle_stats, [BINARY])
    opened: bool = tegrastats.open(interval=INTERVAL)
    logging.debug(f"opened={opened}")
    async with websockets.serve(
        register,
        os.getenv("TEGRASTATS_HOST") or DEFAULT_HOST,
        os.getenv("TEGRASTATS_PORT") or DEFAULT_PORT,
    ):
        await broadcast_stats()


asyncio.run(main())
