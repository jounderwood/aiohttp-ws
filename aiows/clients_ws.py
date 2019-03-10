import asyncio
import logging
from collections import defaultdict

from aiohttp.web_ws import WebSocketResponse

logger = logging.getLogger(__name__)


class _ClientWebSocketsResponses(list):
    """ List of `WebSocketResponse` """

    async def send(self, msg: str):
        await asyncio.gather(*[self._send_safe(ws, msg) for ws in self])

    async def _send_safe(self, ws, msg):
        if not ws.closed:
            await ws.send_str(msg)

    send_str = send  # WebSocketResponse compatibility


class ClientsWebSocketsMap(defaultdict):
    """ Map client_id -> ws list """

    def __init__(self):
        super().__init__(_ClientWebSocketsResponses)

    async def send(self, client_id, msg):
        ws = self.get(client_id)
        if ws:
            await ws.send(msg)
            logger.debug("Send ws message %s to client %r", msg, client_id)
        else:
            logger.debug("Send ws message %s failed, client %r disconnected", msg, client_id)

    async def broadcast(self, msg):
        # TODO: need perf
        for client_id, ws in self.items():
            await ws.send(msg)

    async def add(self, client_id, ws: WebSocketResponse):
        # Why async? Just because!
        self[client_id].append(ws)
        return self[client_id]

    async def close(self, client_id, ws: WebSocketResponse):
        wss = self.get(client_id)
        if wss and ws in wss:
            wss.remove(ws)
            await ws.close()

            if len(wss) == 0:
                del self[client_id]
