"""
pytest setup and helpers
"""
import asyncio
from typing import Union, Type
from dataclasses import dataclass

import pytest
import socketio
from aiohttp import web


@dataclass(frozen=False)
class SioContextInfo:
    port_used: int
    sio_server: socketio.AsyncServer
    app: web.Application
    client: Union[socketio.AsyncClient, socketio.AsyncSimpleClient]


@pytest.fixture
async def sio_context(aiohttp_server,
                      unused_tcp_port_factory,
                      sio_server: socketio.AsyncServer,
                      sio_client_type: Union[Type[socketio.AsyncClient], Type[socketio.AsyncSimpleClient]]):
    """Creates an aihttp server to run the provided sio_server of an free network port.
    And it also generates a connected test client
    Args:
        aiohttp_server (_type_): use fixture to create aiohttp server for pytest
        unused_tcp_port_factory (_type_): use of fixture to get free network port
        sio_server (socketio.AsyncServer): which server instance to use
        sio_client_type (Union[Type[socketio.AsyncClient], Type[socketio.AsyncSimpleClient]]): which kind off client to use

    Yields:
        SioContextInfo: returns dataclass with information about the created context including a test client
    """
    # deactivate monitoring task in python-socketio to avoid errores during shutdown
    sio_server.eio.start_service_task = False

    app = web.Application()
    sio_server.attach(app)
    port_used = unused_tcp_port_factory()
    await aiohttp_server(app, port=port_used)

    client = sio_client_type()
    await client.connect(f'http://localhost:{port_used}',  transports=['websocket'])
    sio_context_info = SioContextInfo(port_used, sio_server, app, client)
    yield sio_context_info

    await client.disconnect()
    """
    Without the sleep you will get the following message:
        Task was destroyed but it is pending!
        task: <Task pending name='Task-9' coro=<AsyncSocket._send_ping() running at .venv/lib/site-packages/engineio/async_socket.py:129> wait_for=<Future pending cb=[Task.task_wakeup()]>>

    No handle available to the ping background task to waitfor it. As alternative give it just a little bit of time.

    Hmm need time to fin the cause and come up with better solution... this increases test time to much
    """
    # await asyncio.sleep(.5)
    await asyncio.sleep(1)
