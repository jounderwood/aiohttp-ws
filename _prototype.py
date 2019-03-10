from aiohttp import web

from datetime import datetime

from aiows import aiows, ActionsRegistry, send, broadcast, send_pubsub

routes = web.RouteTableDef()


aiows = aiows()

actions = ActionsRegistry(prefix='test')

aiows.register_actions(actions)


@routes.get('/ws/')
async def ws(request: web.Request):
    await aiows.client_connect(request, request.query.get('id', 1))


@aiows.on('hello', payload_schema=RequestSchema(), prefix='CWARS')
@aiows.swagger(response_schema=ResponseSchema(), tags=['aaa'])
async def hello_action(payload, client_id):
    return {'mirror': payload}


@aiows.on('update1', swagger=False)
async def update_action(payload, client_id):
    await aiows.send('update_answer', client_id, {'some': 'data'})


@actions.on('update2')
async def update_action(payload, client_id):
    await aiows.broadcast('updated', {'some': 'data'})


@actions.on
async def update_action(payload, client_id):
    await aiows.broadcast('updated', {'some': 'data'})


@aiows.on_pubsub('hello', payload_schema=RequestSchema())
async def hello_action(payload, client_id):
    pass


@aiows.on_pubsub('hello', payload_schema=RequestSchema())
async def hello_action(payload, client_id, request, request_id):
    pass


@aiows.on_error()
async def on_error(payload, client_id):
    pass


@aiows.on_pubsub_error()
async def on_error(payload):
    pass


async def some_worker():
    # From another process
    client_id = 1
    await send(client_id, data={}, request_id=None)
    await broadcast(data={}, request_id=None)
    await send_pubsub(data={}, request_id=None)


app = web.Application()
app.add_routes(routes)
app.add_routes(aiows.swagger(prefix=''))

app.cleanup_ctx.append(aiows.start_ctx)


if __name__ == '__main__':
    import os
    os.environ['YZCONFIG_MODULE'] = 'settings'
    web.run_app(app)
