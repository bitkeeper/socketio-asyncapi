from typing import Union, Literal, Type, Optional
from pydantic import BaseModel

# Write out the supported base type for list and dict: Forward reverences gives problems with resolving for mypy and typeguard
# PAYLOAD_BASE = Union[int, str, bool, dict[str, 'PAYLOAD_BASE'], list['PAYLOAD_BASE']]
PAYLOAD_BASE = Union[int, str, bool, float, dict[str, str], dict[str, int], dict[str, bool], dict[str, float], list[int], list[bool], list[float]]
PAYLOAD_INSTANCES = Optional[Union[BaseModel, PAYLOAD_BASE]]
""" Typed allowed as payload value"""
PAYLOAD_TYPES = Optional[Type[Union[BaseModel, PAYLOAD_BASE]]]
""" Types allowed as payload type"""

NotProvidedType = Literal["NotProvided"]
