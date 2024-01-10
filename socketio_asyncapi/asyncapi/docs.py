"""
AsycnAPI [https://studio.asyncapi.com/] documentation auto generation.
"""
import json
import textwrap
from typing import Callable, Literal, Optional, Type, Union

import yaml
from loguru import logger
from pydantic import BaseModel, schema

from socketio_asyncapi.asyncapi.models.async_api_base import AsyncAPIBase, ChannelItem
from socketio_asyncapi.asyncapi.models.message import Message

from .utils import add_ref_prepath

NotProvidedType = Literal["NotProvided"]

add_description ="""
<br/> AsyncAPI currently does not support Socket.IO binding and Web Socket like syntax used for now.
In order to add support for Socket.IO ACK value, AsyncAPI is extended with with x-ack keyword.
This documentation should **NOT** be used for generating code due to these limitations.
"""

default_channels = yaml.safe_load(
"""
/:
  publish:
    message:
      oneOf:

  subscribe:
    message:
      oneOf:

  x-handlers:
    disconnect: disconnect
"""
)

default_components = yaml.safe_load(
"""
messages:

schemas:
  NoSpec:
    description: Specification is not provided
"""
)


class AsyncAPIDoc(AsyncAPIBase):
    """AsyncAPI documentation generator."""

    @classmethod
    def default_init(cls,
        version: str = "1.0.0",
        title: str = "Demo Chat API",
        description: str = "Demo Chat API",
        server_url: str = "http://localhost:5000",
        server_name: str = "BACKEND",
        server_protocol: str = "socketio",
        server_protocolVersion: str = "5"
    ) -> "AsyncAPIDoc":
        """Initialize AsyncAPI documentation generator."""
        logger.info(f"{server_url=}, {server_name=}, {server_protocol=}")
        default_channels["/"]["subscribe"]["message"]["oneOf"] = []
        default_channels["/"]["publish"]["message"]["oneOf"] = []
        default_components["messages"] = {}
        initial_spec_obj = {
            "info": {
                "title": title,
                "version": version,
                "description": description +
                add_description},
            "servers": {
                server_name: {
                    "url": server_url,
                    "protocol": server_protocol,
                    "protocolVersion": server_protocolVersion
                    }},
            "asyncapi": "2.5.0",
            "channels": default_channels,
            "components": default_components,
        }
        return AsyncAPIDoc.parse_obj(initial_spec_obj)

    def get_yaml(self):
        """Return AsyncAPI documentation in YAML format."""
        return yaml.safe_dump(
            json.loads(
                self.json(
                    by_alias=True,
                    exclude_none=True,
                )
            )
        )

    def add_new_receiver(
            self,
            handler: Callable,
            namespace: Optional[str],
            name: str,
            message_name=None,
            ack_data_model: Optional[Union[Type[BaseModel], NotProvidedType]] = None,
            payload_model: Optional[Union[Type[BaseModel], NotProvidedType]] = None,
        ) -> None:
        if message_name is None:
            message_name = name.title()

        # TODO: make sure schema name is unique
        if ack_data_model == "NotProvided":
            ack = {"$ref": "#/components/schemas/NoSpec"}
        elif isinstance(ack_data_model, type(BaseModel)):
            ack_schema_name = ack_data_model.__name__ # type: ignore
            ack = {"$ref": f"#/components/schemas/{ack_schema_name}"}
            ack_schema = ack_data_model.schema() # type: ignore
            add_ref_prepath(ack_schema, f"/components/schemas/{ack_schema_name}")
            self.components.schemas[ack_schema_name] = ack_schema # type: ignore

        elif ack_data_model:
            ack_schema = {}
            schema.add_field_type_to_schema(ack_data_model, ack_schema)
            if len(ack_schema)>=1:
                ack= ack_schema
            else:
                ack = None
        else:
            ack = None

        if payload_model == "NotProvided":
            payload = {"$ref": "#/components/schemas/NoSpec"}
        elif isinstance(payload_model, type(BaseModel)):
            payload_schema_name = payload_model.__name__ # type: ignore
            payload = {"$ref": f"#/components/schemas/{payload_schema_name}"}
            payload_schema = payload_model.schema() # type: ignore
            add_ref_prepath(payload_schema, f"/components/schemas/{payload_schema_name}")
            self.components.schemas[payload_schema_name] = payload_schema # type: ignore
        elif payload_model:
            payload_schema = {}
            schema.add_field_type_to_schema(payload_model, payload_schema)
            if len(payload_schema)>=1:
                payload= payload_schema
            else:
                payload = None
        else:
            payload = None

        # create new message
        new_message = {
            "name": name,
            "description": handler.__doc__ if  handler.__doc__ else "",
            "x-ack": None,
        }

        # remove multiple spaces so yaml dump does not try to escape them
        if new_message["description"]:
            # add single indent at the beginning if not present
            if not new_message["description"].startswith(" "):
                new_message["description"] = " " + new_message["description"]
            new_message["description"] = textwrap.dedent(new_message["description"])

        new_message["x-ack"] = ack
        new_message["payload"] = payload

        # add message to spec
        if self.components and self.components.messages is not None:
            self.components.messages[message_name] = Message.parse_obj(new_message)

        # add to sub
        one_of = {"$ref": f"#/components/messages/{message_name}"}
        channel = self._get_channel(namespace)
        if channel:
              channel.publish.message.__dict__["oneOf"].append(one_of)

    def add_new_sender(
            self,
            namespace: None,
            event: str,
            payload_model: Optional[Union[Type[BaseModel], NotProvidedType]] = None,
            description: Optional[str] = None,
        ) -> None:
        """Generate new sender documentation for AsyncAPI."""
        if payload_model == "NotProvided":
            payload = {"$ref": "#/components/schemas/NoSpec"}
        elif isinstance(payload_model, type(BaseModel)):
            payload_schema_name = payload_model.__name__ # type: ignore
            payload_schema = payload_model.schema() # type: ignore
            payload = {"$ref": f"#/components/schemas/{payload_schema_name}"}
            add_ref_prepath(payload_schema, f"/components/schemas/{payload_schema_name}") # type: ignore
            self.components.schemas[payload_schema_name] = payload_schema # type: ignore
        elif payload_model:
            payload_schema = {}
            schema.add_field_type_to_schema(payload_model, payload_schema)
            if len(payload_schema)>=1:
                payload= payload_schema
            else:
                payload = None
        else:
            payload = None

        # create new message
        new_message = {
            "name": event,
            "description": description if description else "",
            "payload": payload,
        }

        # remove multiple spaces so yaml dump does not try to escape them
        if new_message["description"]:
            # add single indent at the beginning if not present
            if not new_message["description"].startswith(" "):
                new_message["description"] = " " + new_message["description"]
            new_message["description"] = textwrap.dedent(new_message["description"])

        # add message to spec
        if self.components and self.components.messages is not None:
            self.components.messages[event] = Message.parse_obj(new_message)

        # add to pub
        one_of = {"$ref": f"#/components/messages/{event}"}
        channel = self._get_channel(namespace)
        if channel:
              channel.subscribe.message.__dict__["oneOf"].append(one_of)

    def _get_channel(self, namespace: Optional[str]) ->ChannelItem:
        '''Get specific channel, if not already present create it'''
        channel_id: str = namespace if namespace else '/'
        if channel_id not in self.channels:
            self.channels[channel_id] = ChannelItem.parse_obj(
                                        {
                                        "publish": {
                                            "message": {
                                            "oneOf": []
                                            }
                                        },
                                        "subscribe": {
                                            "message": {
                                            "oneOf": []
                                            }
                                        }
                                        }
                                    )
        return self.channels[channel_id]
