import pytest

from marshmallow import Schema, fields
from aiohttp_ws.actions_registry import ActionsRegistry


class Incoming(Schema):
    id = fields.Int(required=True)


@pytest.fixture
def actions():
    return ActionsRegistry()


@pytest.mark.asyncio
async def test_no_type(actions):
    @actions.on
    async def test_no_type_action(msg, client_id):
        pass

    assert 'TEST_NO_TYPE_ACTION' in actions
    assert actions['TEST_NO_TYPE_ACTION'].payload_schema is None


@pytest.mark.asyncio
async def test_no_type2(actions):
    @actions.on()
    async def test_no_type2_action(msg, client_id):
        pass
    assert 'TEST_NO_TYPE2_ACTION' in actions


@pytest.mark.asyncio
async def test_prefix(actions):
    @actions.on('act', prefix='test', payload_schema=Incoming())
    async def test_action(msg, client_id):
        pass
    assert 'TEST_ACT' in actions
    assert isinstance(actions['TEST_ACT'].payload_schema, Incoming)


@pytest.mark.asyncio
async def test_action_type_formatting(actions):
    @actions.on(action_type='UPDATE_something ', prefix='   prefIx')
    async def test_action(msg, client_id):
        pass
    assert 'PREFIX_UPDATE_SOMETHING' in actions
