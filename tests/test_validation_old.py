import asyncio
import pytest
import json
# from flask_socketio import SocketIOTestClient
from socketio import AsyncSimpleClient
from socketio.exceptions import TimeoutError as SIOTimeoutError

# from socketio_asyncapi import AsyncAPISocketIO

from socketio_asyncapi import RequestValidationError, ResponseValidationError, EmitValidationError
from .fixtures import downloader_queue
from .fixtures import socketio as sio_server


TIMEOUT_1SEC: int= 1

SIO_CONNECT_CFG= ['sio_server,sio_client_type', [(sio_server, AsyncSimpleClient)]]


# _ = client

@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_request_validation(sio_context):
    client = sio_context.client
    data ={
        "url": "https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885__480.jpg",
        "location": "/tmp/tree.jpg",
    }
    ack = await client.call('download_file', data)
    assert json.loads(ack) == {'success': True, 'error': None, 'data': {'is_accepted': True}}
    assert len(downloader_queue) == 1
    assert downloader_queue[0].url == "https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885__480.jpg"
    assert downloader_queue[0].check_hash == False

@pytest.mark.parametrize(*SIO_CONNECT_CFG)
@pytest.mark.asyncio
async def test_request_validation_fail(sio_context):
    client = sio_context.client
    data ={
        "url": "https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885__480.jpg",
    }
    ack = await client.call('download_file', data)
    ack_msg =  json.loads(ack)
    assert ack_msg['success'] == False
    assert "1 validation error " in ack_msg['error']
    #TODO: check validate the result model


@pytest.mark.parametrize(*SIO_CONNECT_CFG)
async def test_emit_validation(sio_context):
    client = sio_context.client

    r_data = {"downloader_queue": [
        "https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885__480.jpg",
        "https://cdn.pixabay.com/photo/2015/04/23/22/00/tree-736885__480.jpg", ]}
    await sio_context.sio_server.emit('current_list', r_data)

    event_data = await client.receive(TIMEOUT_1SEC)
    assert len(event_data) == 2

@pytest.mark.parametrize(*SIO_CONNECT_CFG)
async def test_emit_validation_fail(sio_context):
    client = sio_context.client
    with pytest.raises(EmitValidationError) as exc_info:
        await sio_context.sio_server.emit('current_list', {"downloader_queue": [ "WRONG_URL",]})

    # don't expect an event is send on emit exception
    with pytest.raises(SIOTimeoutError) as exc_info:
        event_data = await client.receive(TIMEOUT_1SEC)
