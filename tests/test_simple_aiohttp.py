"""
Test the sio_context with
"""
# stdlib imports
import asyncio

# 3rd party imports
import pytest
import socketio

from . import appdummy as main

SIO_CONNECT_CFG = ['sio_server,sio_client_type',
                   [(main.sio, socketio.AsyncClient)]]


@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_chat_simple(sio_context):
    """A simple websocket test"""
    sio = sio_context.client

    future = asyncio.get_running_loop().create_future()

    @sio.on('chat message')
    def on_message_received(data):
        print(f"Client received: {data}")
        # set the result
        future.set_result(data)

    message = 'Hello!'
    print(f"Client sends: {message}")
    await sio.emit('chat message', message)
    # wait for the result to be set (avoid waiting forever)
    await asyncio.wait_for(future, timeout=1.0)
    assert future.result() == message
