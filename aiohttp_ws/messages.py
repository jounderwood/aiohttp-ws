import json
import logging
from typing import Union

from aiohttp.web_ws import WebSocketResponse

from aiohttp_ws.constants import MSG_DESTINATION_KEY, MessageCustomDestinations, ErrorActionTypes
from aiohttp_ws.exceptions import RequestValidationError
from aiohttp_ws.utils.format import camelcase
from .redis import get_redis_lazy
from .settings import settings

logger = logging.getLogger(__name__)


def _form_message(payload=None, action_type=None, request_id=None, to_camelcase=True):
    msg = {
        'action_type': action_type,
        'payload': payload or {},
        'request_id': request_id,
    }
    if to_camelcase and settings.CAMEL_CASE_TRANSFORM:
        msg = camelcase(msg)

    return msg


def _form_error_msg(exc: Union[str, Exception]='Server error', **kwargs):
    payload = {
        'message': str(exc),
        'errors': {},
    }

    if isinstance(exc, RequestValidationError):
        payload['message'] = 'ValidationError'
        payload['errors'] = exc.normalized_messages()
        action_type = ErrorActionTypes.VALIDATION_ERROR
    else:
        action_type = ErrorActionTypes.SERVER_ERROR

    if 'action_type' not in kwargs:
        kwargs['action_type'] = action_type

    return _form_message(payload, **kwargs)


async def _generic_send_via_pubsub(destination, payload=None, action_type=None, request_id=None, **kwargs):
    redis = await get_redis_lazy()

    msg = _form_message(payload, action_type, request_id, **kwargs)
    msg[MSG_DESTINATION_KEY] = destination

    res = await redis.publish(settings.PUBSUB_CHANNEL_NAME, json.dumps(msg))
    return res == 1


async def send(client_id, payload=None, action_type=None, request_id=None, **kwargs):
    return await _generic_send_via_pubsub(client_id, payload, action_type, request_id, **kwargs)


async def send_directly(ws: WebSocketResponse, payload=None, action_type=None, request_id=None, **kwargs):
    msg = _form_message(payload, action_type, request_id, **kwargs)
    return await ws.send_str(json.dumps(msg))


async def broadcast(payload=None, action_type=None, request_id=None, **kwargs):
    return await _generic_send_via_pubsub(
        MessageCustomDestinations.BROADCAST, payload, action_type, request_id, **kwargs
    )


async def send_pubsub(payload=None, action_type=None, request_id=None, **kwargs):
    kwargs['to_camelcase'] = False
    return await _generic_send_via_pubsub(
        MessageCustomDestinations.BACKEND, payload, action_type, request_id, **kwargs
    )


async def send_error_directly(ws: WebSocketResponse, *args, **kwargs):
    msg = _form_error_msg(*args, **kwargs)
    return await ws.send_str(json.dumps(msg))
