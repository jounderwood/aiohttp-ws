from .service import Service
from .actions_registry import ActionsRegistry
from .messages import send, send_directly, send_pubsub, broadcast


def aiows():
    return Service()
