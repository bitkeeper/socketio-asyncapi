"""
This test the use of custom exception handlers for:
* server received messages type fail
* server returned acknowledge (response) type fail
* server send message type fail
"""

import asyncio
import pytest
from socketio import AsyncSimpleClient
from socketio_asyncapi import AsyncAPISocketIO
from socketio_asyncapi import RequestValidationError, ResponseValidationError, EmitValidationError


TIMEOUT_1SEC: int = 1


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


@pytest.mark.parametrize('model_type,model_value', [(int, "dsd")])
@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_default_exception_handler_receive(sio_context, model_type, model_value):
    future = asyncio.get_running_loop().create_future()

    event_name = 'message_type_validation_fail'
    remove_event_handler(event_name)

    @sio.on_error_default
    async def handler_exception(exp: Exception):
        # just return, results in no acknowledge
        future.set_result(exp)
        return

    @sio.on(event_name)
    async def on_message_received(sid, data: model_type) -> model_type:
        return

    await sio_context.client.emit(event_name, model_value)
    await asyncio.wait_for(future, timeout=TIMEOUT_1SEC)

    exc = future.result()
    assert isinstance(exc, RequestValidationError)


@pytest.mark.parametrize('model_type,model_value', [(int, "dsd")])
@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_default_exception_handler_response(sio_context, model_type, model_value):
    future = asyncio.get_running_loop().create_future()

    event_name = 'message_type_validation_fail'
    remove_event_handler(event_name)

    @sio.on_error_default
    async def handler_exception(exp: Exception):
        if isinstance(exp, ResponseValidationError):
            future.set_result(exp)
        # just return, results in no acknowledge
        return

    @sio.on(event_name)
    async def on_message_received(sid) -> model_type:
        return model_value

    ack = await sio_context.client.emit(event_name)
    assert ack is None

    await asyncio.wait_for(future, timeout=TIMEOUT_1SEC)


@pytest.mark.parametrize('model_type,model_value', [(int, "dsd")])
@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_default_exception_handler_emit(sio_context, model_type, model_value):
    future = asyncio.get_running_loop().create_future()

    event_name = 'message_type_validation_fail'
    remove_event_handler(event_name)

    @sio.on_error_default
    async def handler_exception(exp: Exception):
        if isinstance(exp, EmitValidationError):
            future.set_result(exp)
        # reraise exeception to ensure exception is also 'seen' by caller
        raise exp

    @sio.doc_emit(event_name, model_type)
    async def dummy():
        pass

    with pytest.raises((EmitValidationError, EmitValidationError)):
        await sio.emit(event_name, model_value)
    await asyncio.wait_for(future, timeout=TIMEOUT_1SEC)


@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_default_exception_handler_type_fail(sio_context):
    with pytest.raises(ValueError):
        # surpress wrong type; async is missing
        # this should also be detected on runtime:
        @sio.on_error_default  # type: ignore
        def handler_exception(exp: int):
            pass

    with pytest.raises(ValueError):
        # surpress wrong type; async is missing
        # this should also be detected on runtime:
        sio.on_error_default(None)  # type: ignore
