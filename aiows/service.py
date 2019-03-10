import json
import logging
from asyncio import CancelledError
from types import coroutine

from aiohttp import web
from aioredis import Redis, Channel

from .actions_registry import ActionsRegistry
from .clients_ws import ClientsWebSocketsMap
from .constants import MessageCustomDestinations, MSG_DESTINATION_KEY
from .exceptions import RequestValidationError
from .messages import send, send_directly, send_pubsub, broadcast, send_error_directly
from .redis import get_redis_lazy, open_pubsub_channel, close_redis
from .settings import settings
from .utils.format import underscore

logger = logging.getLogger(__name__)


class Service:
    redis_pubsub: Redis
    pubsub_channel: Channel

    pubsub_to_ws_task: coroutine

    websockets: ClientsWebSocketsMap

    ws_actions: ActionsRegistry
    pubsub_actions: ActionsRegistry

    send = staticmethod(send)
    send_directly = staticmethod(send_directly)
    send_pubsub = staticmethod(send_pubsub)
    broadcast = staticmethod(broadcast)

    def __init__(self):
        self.websockets = ClientsWebSocketsMap()
        self.ws_actions = ActionsRegistry()
        self.pubsub_actions = ActionsRegistry()

    def register_actions(self, actions: ActionsRegistry):
        for action_type, action in actions.items():
            if action_type in self.ws_actions:
                raise ValueError('Action type `%s` already registered' % action.action_type)

            self.ws_actions[action_type] = action

    def on(self, action_type: str = None, payload_schema=None, prefix=None):
        return self.ws_actions.on(action_type, payload_schema, prefix)

    def on_pubsub(self, action_type: str = None, payload_schema=None, prefix=None):
        return self.pubsub_actions.on(action_type, payload_schema, prefix)

    async def client_connect(self, request, client_id):
        ws_response = web.WebSocketResponse(autoping=settings.AUTOPING, heartbeat=settings.HEARTBEAT)
        await ws_response.prepare(request)

        logger.debug("New WS connection, client_id - %r, %s", client_id, ws_response)

        try:
            await self.websockets.add(client_id, ws_response)

            async for msg in ws_response:
                logger.debug("WS %r get message - %s", client_id, msg)
                if msg.data == 'close':
                    await self.websockets.close(client_id, ws_response)
                else:
                    await self._call_action(client_id, msg, request, ws_response)
        except CancelledError:
            logger.debug("WS %r %s CancelledError", client_id, ws_response)
        finally:
            await self.websockets.close(client_id, ws_response)
            logger.debug("WS %r %s connection closed", client_id, ws_response)

        return ws_response

    async def _call_action(self, client_id, msg, request, ws_response):
        try:
            msg = underscore(json.loads(msg.data))
            await self.ws_actions.call_action(msg, client_id, request=request, initiator=ws_response)
        except (ValueError, TypeError) as e:
            logger.exception("Failed to parse ws msg as json")
            await send_error_directly(ws_response, exc=e)
        except RequestValidationError as e:
            logger.exception("WS action validation error, client - %r, message - %s", client_id, msg)
            await send_error_directly(ws_response, exc=e, request_id=msg.get('request_id'))
        except Exception:
            logger.exception("Failed to process incoming msg")
            await send_error_directly(ws_response, request_id=msg.get('request_id'))

    async def start_ctx(self, app):
        self.redis_pubsub = await get_redis_lazy()
        self.pubsub_to_ws_task = app.loop.create_task(self.handle_pubsub_messages())
        yield
        self.pubsub_to_ws_task.cancel()
        await close_redis()

    async def handle_pubsub_messages(self):
        """ Async task that subscribes to redis pub/sub channel and sends recieved messages
        from pub/sub to WS clients"""

        try:
            async with open_pubsub_channel(settings.PUBSUB_CHANNEL_NAME) as channel:
                self.pubsub_channel = channel
                logger.info("Redis pubsub channel installed, %r", channel)
                while await channel.wait_message():
                    try:
                        msg = await channel.get_json()
                        await self._handle_pubsub_message(msg)
                    except (ValueError, TypeError):
                        logger.exception("Failed to parse pub/sub msg as json")
                    except Exception:
                        logger.exception("Pub/sub message handle error")
        except CancelledError:
            pass
        except Exception as e:
            logger.exception(e)
        finally:
            self.pubsub_channel = None

    async def _handle_pubsub_message(self, msg: dict):
        destination = msg.pop(MSG_DESTINATION_KEY, None)

        logger.debug("Redis pubsub got message %s to %r", msg, destination)

        if destination == MessageCustomDestinations.BACKEND:
            try:
                await self.pubsub_actions.call_action(underscore(msg), client_id=None)
            except Exception as e:
                logger.exception('Pub/sub action error %s', str(e))
        elif destination == MessageCustomDestinations.BROADCAST:
            await self.websockets.broadcast(json.dumps(msg))
        else:
            await self.websockets.send(destination, json.dumps(msg))
