"""
This test test the type validation of:
* server received messages
* server returned acknowledge (response)
* server send message
"""


import asyncio
import pytest
from pydantic import BaseModel
from socketio import AsyncSimpleClient
from socketio_asyncapi import AsyncAPISocketIO

from socketio_asyncapi import EmitValidationError


TIMEOUT_1SEC: int = 1


class DummyModel(BaseModel):
    """ Test model used to test pydantic BaseModel payload"""
    my_message:  str
    my_flag: bool


sio = AsyncAPISocketIO(
    async_mode='aiohttp',
    validate=True,
    generate_docs=True,
    version="1.0.0",
    title="Dummy API for test",
    description="Server pytest API",
    server_url="http://localhost:5000",
    server_name="PYTEST_BACKEND",
    logger=True,
    engineio_logger=True,
    ping_interval=.5
)
""" An socketio test server"""


def remove_event_handler(event_name: str) -> None:
    """You can't register an doc_emit with a different model type.
    For the test this function will remove it from the socket server"""
    if event_name in sio.emit_models:
        del sio.emit_models[event_name]


SIO_CONNECT_CFG = ['sio_server,sio_client_type', [(sio, AsyncSimpleClient)]]


@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_request_non_type(sio_context):
    future = asyncio.get_running_loop().create_future()

    @sio.on('message_non_type')
    async def on_message_received(sid, data):
        print(f"Server received: {data}")
        future.set_result(data)

    message = 'Hello!'
    print(f"Client sends: {message}")
    await sio_context.client.emit('message_non_type', message)

    await asyncio.wait_for(future, timeout=1.0)
    assert future.result() == message


@pytest.mark.parametrize('model_type,model_value', [(int, 42),
                                                    (str, 'foobar'),
                                                    (dict, dict(a=4, b=5)),
                                                    (DummyModel, DummyModel(
                                                        my_message="foobar", my_flag=True).dict())
                                                    ])
@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_request_validation(sio_context, model_type, model_value):
    future = asyncio.get_running_loop().create_future()

    event_name = 'message_type_validation'
    remove_event_handler(event_name)

    @sio.on(event_name)
    async def on_message_received(sid, data: model_type):
        print(f"Server received: {data}")
        future.set_result(data)

    await sio_context.client.emit(event_name, model_value)

    await asyncio.wait_for(future, timeout=1.0)
    assert future.result() == model_value


@pytest.mark.parametrize('model_type,model_value', [(int, "dsd"),
                                                    # (str, DummyModel(my_message="foobar", my_flag=True).dict()), # < this valid
                                                    (str, None),
                                                    (dict, 42),
                                                    (DummyModel, 42),
                                                    (DummyModel, {
                                                     "my_message": "foobar", "my_not_flag": True})
                                                    ])
@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_request_validation_fail(sio_context, model_type, model_value):
    future = asyncio.get_running_loop().create_future()

    event_name = 'message_basic_type_fail'
    remove_event_handler(event_name)

    @sio.on(event_name)
    async def on_message_received(sid, data: model_type):
        print(f"Server received: {data}")
        future.set_result(data)

    await sio_context.client.emit(event_name, model_value)

    with pytest.raises(asyncio.exceptions.TimeoutError):
        await asyncio.wait_for(future, timeout=1.0)


@pytest.mark.parametrize('model_type,model_value', [(int, 42),
                                                    (str, 'foobar'),
                                                    (dict, dict(a=4, b=5)),
                                                    (DummyModel, DummyModel(
                                                        my_message="foobar", my_flag=True))
                                                    ])
@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_acknowledge_validation(sio_context, model_type, model_value):
    event_name = 'message_type_validation'
    remove_event_handler(event_name)

    @sio.on(event_name)
    async def on_message_received(sid) -> model_type:
        return model_value

    ack = await sio_context.client.call(event_name, None)

    compare_type_to = dict if issubclass(model_type, BaseModel) else model_type
    compare_value_to = model_value.dict() if issubclass(
        model_type, BaseModel) else model_value

    assert isinstance(ack, compare_type_to)
    assert ack == compare_value_to


@pytest.mark.parametrize('model_type,model_value', [(int, "dsd"),
                                                    # (str, DummyModel(my_message="foobar", my_flag=True).dict()), # < this valid
                                                    (str, None),
                                                    (dict, 42),
                                                    (DummyModel, 42),
                                                    (DummyModel, {
                                                     "my_message": "foobar", "my_not_flag": True})
                                                    ])
@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_acknowledge_validation_fail(sio_context, model_type, model_value):
    event_name = 'message_type_validation_fail'
    remove_event_handler(event_name)

    @sio.on(event_name)
    async def on_message_received(sid) -> model_type:
        return model_value

    ack = await sio_context.client.call(event_name, None)
    assert ack is None


@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_emit_non_type_validation(sio_context):
    @sio.doc_emit('emit_notype', None)
    async def dummy():
        pass

    await sio.emit('emit_notype')


@pytest.mark.parametrize('model_type,model_value', [(int, 42),
                                                    (str, 'foobar'),
                                                    (dict, dict(a=4, b=5)),
                                                    (DummyModel, DummyModel(
                                                        my_message="foobar", my_flag=True))
                                                    ])
@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_emit_type_validation(sio_context, model_type, model_value):
    event_name = 'emit_type_validation'
    remove_event_handler(event_name)

    @sio.doc_emit(event_name, model_type)
    async def dummy():
        pass

    await sio.emit(event_name, model_value)


@pytest.mark.parametrize('model_type,model_value', [(int, "dsd"),
                                                    #   (str, DummyModel(my_message="foobar", my_flag=True).dict()),
                                                    (str, None),
                                                    (dict, 42),
                                                    (DummyModel, 42),
                                                    (DummyModel, {
                                                     "my_message": "foobar", "my_not_flag": True})
                                                    ])
@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_emit_type_validation_fail(sio_context, model_type, model_value):
    event_name = 'emit_type_validation_fail'
    remove_event_handler(event_name)

    @sio.doc_emit(event_name, model_type)
    async def dummy():
        pass

    with pytest.raises((EmitValidationError, EmitValidationError)):
        await sio.emit(event_name, model_value)
