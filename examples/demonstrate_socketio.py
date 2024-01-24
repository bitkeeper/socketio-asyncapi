#!/usr/bin/env python

'''
Demonstrates the use of socketio_asyncapi:
- starts a socketio server
- show several constructions how to expose subscribers and publishers
- generate a asyncapi yml spec
- provides an html renderer of the spec at http://localhost:5010/docs?spec=/asyncapi.yml



http://localhost:5010/docs?spec=/asyncapi.yml
'''

import pathlib
import uvicorn
import socketio  # type: ignore
from socketio_asyncapi import AsyncAPISocketIO
from pydantic import BaseModel, Field

# On startup the app will generate a static file with the asyncapi on the following location
asyncapi_specfile_path = pathlib.Path(pathlib.Path(__file__).parent / "demonstrate_socketio.autogen.yml")

# Where to asyncapi renderer (makes use of AsyncAPI react standalone component)
asyncapi_renderer = pathlib.Path(pathlib.Path(__file__).parent / "asyncapi_renderer" / "index.html")

sio = AsyncAPISocketIO(
    validate=True,
    generate_docs=True,
    version="1.0.0",
    title="Demo",
    description="Demo Server",
    server_url="http://localhost:5010",
    server_name="DEMO_SIO",
    async_mode='asgi'
    # ,
    # cors_allowed_origins= [
    #     'http://localhost:5010',
    # ]
)

app = socketio.ASGIApp(sio, static_files={
    '/docs': str(asyncapi_renderer),
    '/asyncapi.yml': str(asyncapi_specfile_path)
})

background_task_started = False


class MyDataModel(BaseModel):
    """Example datamodel"""
    message: str = Field(..., description="Your message", example="foobar")


class MyDataModel2(BaseModel):
    """Example of different datamodel"""
    message: str = Field(..., description="Your message", example="foobar")


async def background_task():
    """Example of how to send server generated events to clients."""
    count = 0
    while True:
        await sio.sleep(10)
        count += 1
        await sio.emit('my_response', {'data': 'Server generated event'})


@sio.on('get_asyncapi_yaml', get_from_typehint=True)
async def test_docs(sid, message) -> str:
    ''' generate and returns a asyncapi yaml schema'''
    return sio.asyncapi_doc.get_yaml()


@sio.on('my_event_no_typing', get_from_typehint=False)
async def test_no_typing(sid, message):
    '''demonstrates and receive event and emit without type information (dict used)'''
    await sio.emit('my_response', {'data': message['data']}, room=sid)

# ----------------------------------------------------------------
# native types
# ----------------------------------------------------------------


@sio.on('my_event_dict')
async def test_as_dict(sid, message: dict):
    '''demonstrates and receive event, payload as dict and emit without type information (dict used)'''
    await sio.emit('my_response', {'data': message['data']}, room=sid)


@sio.doc_emit('my_response_dict', dict[str, str])
@sio.on('my_event_and_emit_dict')
async def test_as_dict_2(sid, message: dict):
    '''demonstrates and receive event and emit payload as dict '''
    await sio.emit('my_response_dict', {'data': message['data']}, room=sid)


@sio.doc_emit('my_response_str', str)
@sio.on('my_event_and_emit_str')
async def test_as_str(sid, message: str):
    '''demonstrates and receive event and emit payload as str '''
    await sio.emit('my_response_str', message, room=sid)


@sio.doc_emit('my_response_str', str)
@sio.on('my_event_and_emit_str_with_ack')
async def test_as_str_2(sid, message: str) -> str:
    '''demonstrates and receive event and emit payload as str '''
    await sio.emit('my_response_str', message, room=sid)
    return message

# ----------------------------------------------------------------
# pydantic base models
# ----------------------------------------------------------------


@sio.doc_emit('my_response_basemodel', MyDataModel)
@sio.on('my_event_basemodel')
async def test_basemodel(sid, message: MyDataModel):
    ''' demonstrates use of a pydantic basemodel for event receive and emit'''
    await sio.emit('my_response_basemodel', MyDataModel(message=message.message), room=sid)


@sio.doc_emit('my_response_basemodel', MyDataModel)
@sio.on('my_event_basemodel_with_ack')
async def test_basemodel_2(sid, message: MyDataModel) -> MyDataModel:
    ''' demonstrates use of a pydantic basemodel for event receive, emit and acknowledge'''
    await sio.emit('my_response_basemodel', MyDataModel(message=message.message), room=sid)
    return MyDataModel(message=message.message)

# ----------------------------------------------------------------
# namespaces
# ----------------------------------------------------------------


@sio.doc_emit('my_response_basemodel', MyDataModel, namespace='/ns1')
@sio.on('my_event_ns', namespace='/ns1')
async def test_basemodel_ns(sid, message: MyDataModel):
    ''' demonstrates use of a pydantic basemodel for event receive and emit'''
    pass
    await sio.emit('my_response_basemodel', MyDataModel(message=message.message), room=sid)


@sio.on('connect')
async def test_connect(sid, environ):
    global background_task_started
    if not background_task_started:
        sio.start_background_task(background_task)
        background_task_started = True
    await sio.emit('my_response', {'data': 'Connected', 'count': 0}, room=sid)


@sio.on('disconnect')
async def test_disconnect(sid):
    print('Client disconnected')


if __name__ == '__main__':
    doc_str = sio.asyncapi_doc.get_yaml()
    with open(asyncapi_specfile_path, "w") as f:
        f.write(doc_str)

    uvicorn.run(app, host='127.0.0.1', port=5010)
