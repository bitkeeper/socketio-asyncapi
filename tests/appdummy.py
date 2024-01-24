"""
Dummy socketio example app  with aiohttp as webserver
"""
import socketio   # type: ignore[import-untyped]
from aiohttp import web


async def startup():
    print("Starting Application")


async def shutdown():
    print("Shutdown Application")


# For aiohttp test server
sio = socketio.AsyncServer(
    async_mode='aiohttp', logger=True, engineio_logger=True,  ping_interval=.5)


# For uvicorn test server
# sio = socketio.AsyncServer(async_mode='asgi',logger=True, engineio_logger=True, monitor_clients = False, ping_interval=.5 , ping_timeout =.5)
# app.mount('/sio', socketio.ASGIApp(sio))  # socketio adds automatically /socket.io/ to the URL.
# app = socketio.ASGIApp(sio, on_startup=startup, on_shutdown=shutdown)  # socketio adds automatically /socket.io/ to the URL.


@sio.on('connect')  # type: ignore[reportOptionalCall]
async def sio_connect(sid, environ):
    """Track user connection"""
    print('A user connected')


@sio.on('disconnect')  # type: ignore[reportOptionalCall]
async def sio_disconnect(sid):
    """Track user disconnection"""
    print('User disconnected')


@sio.on('chat message')  # type: ignore[reportOptionalCall]
async def chat_message(sid, msg):
    """Receive a chat message and send to all clients"""
    print(f"Server received: {msg}")
    await sio.emit('chat message', msg)

if __name__ == '__main__':
    app = web.Application()
    sio.attach(app)

    web.run_app(app)
