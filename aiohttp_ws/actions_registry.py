import inspect
import logging
from collections import OrderedDict
from typing import Callable

from aiohttp.web_request import Request
from aiohttp.web_ws import WebSocketResponse
from marshmallow import Schema
from marshmallow import ValidationError

from aiohttp_ws.exceptions import RequestValidationError
from aiohttp_ws.messages import send_directly
from aiohttp_ws.utils.format import underscore_text
from aiohttp_ws.utils.inspect import Spec

logger = logging.getLogger(__name__)


class Action:
    __slots__ = ('handler', 'action_type', 'payload_schema', 'spec')
    _allowed_args = ('payload', 'client_id', 'request', 'request_id', 'action_type')

    def __init__(self, handler: Callable, action_type: str = None, payload_schema=None, prefix=None):
        self.handler = handler

        if inspect.isclass(payload_schema) and issubclass(payload_schema, Schema):
            self.payload_schema = payload_schema()
        else:
            self.payload_schema = payload_schema

        self.action_type = action_type and action_type.strip() or underscore_text(handler.__name__)
        if prefix:
            self.action_type = f'{prefix.strip()}_{self.action_type}'
        self.action_type = self.action_type.upper()

        self.spec = Spec.get(handler)

    async def call(self, msg: dict, client_id, request: Request = None, ws: WebSocketResponse = None):
        payload = msg.get('payload')
        request_id = msg.get('request_id')

        if self.payload_schema:
            try:
                payload = self.payload_schema.load(payload)
            except ValidationError as e:
                raise RequestValidationError(*e.args) from e

        args = OrderedDict((
            ('payload', payload),
            ('client_id', client_id),
            ('request', request),
            ('request_id', request_id),
            ('action_type', self.action_type),
            ('ws', ws),
        ))

        if self.spec.has_args or self.spec.has_kwargs:
            result = await self.handler(**args)
        else:
            total = len(self.spec.args)
            for i, key in enumerate(args.copy()):
                if i + 1 > total:
                    del args[key]
            result = await self.handler(**args)

        if isinstance(result, tuple):
            response_action_type, response_payload = result
            await send_directly(
                ws,
                payload=response_payload,
                action_type=response_action_type,
                request_id=request_id
            )


class ActionsRegistry(dict):
    prefix = None

    def __init__(self, prefix=None):
        super().__init__()
        self.prefix = prefix

    def on(self, action_type: str = None, payload_schema=None, prefix=None):
        handler = None
        if callable(action_type):
            handler = action_type
            action_type = None

        def _on(handler):
            action = Action(handler, action_type, payload_schema, prefix or self.prefix)

            if action.action_type in self:
                raise ValueError('Action type `%s` already registered' % action.action_type)

            self[action.action_type] = action

            return handler

        return _on(handler) if handler else _on

    async def call_action(self, msg: dict, client_id, request: Request = None, initiator: WebSocketResponse = None):
        action_type = msg.get('action_type', '').strip().upper()
        if action_type not in self:
            raise RequestValidationError("Action %s is not supported" % action_type)

        return await self[action_type].call(msg, client_id, request, initiator)
