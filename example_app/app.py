import os
os.environ["YZCONFIG_MODULE"] = "example_app.settings"

from os.path import dirname, join
import logging

import aiohttp_jinja2
import jinja2
from aiohttp import web

from aiohttp_ws import aiohttp_ws
from .another_actions import actions

logging.basicConfig(level=logging.DEBUG)

app = web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(join(dirname(__file__), "jinja2")))
ws_service = aiohttp_ws()
routes = web.RouteTableDef()


@routes.get("/stats/")
async def stats(request: web.Request):
    return web.Response(text="%r" % ws_service.websockets)


@routes.get("/ws/")
async def ws(request: web.Request):
    return await ws_service.client_connect(request, request.query.get("id", 1))


@ws_service.on("direct_mirror", prefix="root")
async def mirror_direct_answer(payload):
    return "i_am_mirror", payload


@ws_service.on
async def mirror_broadcast(payload):
    await ws_service.broadcast(payload, action_type="mirror_broadcast")


@ws_service.on_pubsub(action_type="notify_preprocess")
async def from_backend(payload):
    """
    redis-cli
    127.0.0.1:6379> PUBLISH ws_service '{"action_type": "notify_preprocess", "payload":{"users": [1,2,3]}, "_destination": "backend"}'
    """
    raise Exception(payload["users"])


@routes.get("/")
@aiohttp_jinja2.template("jinja2/ws_test.html")
async def ws_test(request):
    actions = {}
    for action in ws_service.ws_actions:
        actions[action] = {}
        # data = schema and generate_data_by_schema(schema())
        # actions[action] = data and schema().dumps(data) or None

    context = {"request": request, "client_id": request.query.get("id", 1), "actions": actions}
    response = aiohttp_jinja2.render_template("ws_test.html", request, context)
    return response


app.add_routes(routes)
ws_service.register_actions(actions)
app.cleanup_ctx.append(ws_service.start_ctx)


if __name__ == "__main__":
    web.run_app(app)
