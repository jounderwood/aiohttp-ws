import logging

from aiows import ActionsRegistry, send
from marshmallow import Schema, fields

logger = logging.getLogger(__name__)
actions = ActionsRegistry(prefix='not_root')


class MessageToClient(Schema):
    client_id = fields.Int(required=True)
    message = fields.Str(required=True)


@actions.on(payload_schema=MessageToClient())
async def send_to_client(payload, **kwargs):
    logger.info('Action parameters %s %s', payload, kwargs)
    await send(payload['client_id'], payload['message'])
