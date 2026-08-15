"""Hoymiles G3 hybrid inverter — async Modbus-TCP telemetry reader."""

__version__ = "0.2.1"

from .decode import decode_ascii_string, decode_words
from .registers import Register

from .config import InverterConfig, InverterInfo
from .inverter import Inverter
from .groups import group_names

__all__ = [
    "__version__",
    "Inverter",
    "InverterConfig",
    "group_names",
    "InverterInfo",
    "Register",
    "decode_words",
    "decode_ascii_string",
]
