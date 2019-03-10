import logging
from marshmallow import Schema, fields

from aiohttp_ws import ActionsRegistry, send

logger = logging.getLogger(__name__)
actions = ActionsRegistry(prefix="not_root")


class MessageToClient(Schema):
    client_id = fields.Int(required=True)
    message = fields.Str(required=True)


@actions.on(payload_schema=MessageToClient())
async def send_to_client(payload, **kwargs):
    logger.info("Action parameters %s %s", payload, kwargs)
    await send(str(payload["client_id"]), payload["message"])
