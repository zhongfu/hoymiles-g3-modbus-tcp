"""Decode raw 16-bit words into typed values."""
from __future__ import annotations

import struct

from .registers import WSIZE


def decode_words(words, dtype, scale=1.0) -> int | float:
    """Decode ``words`` (list of 16-bit ints) of ``dtype``, then divide by ``scale``."""
    if dtype in ("U16", "I16"):
        v = words[0]
        if dtype == "I16" and v >= 0x8000:
            v -= 0x10000
    elif dtype in ("I32", "H32", "F32", "I32R"):
        if dtype == "F32":
            v = struct.unpack(">f", struct.pack(">HH", words[0], words[1]))[0]
        elif dtype == "I32R":
            # Reversed 32-bit: the LOW word is stored first (register addr),
            # the HIGH word at addr+1. Used by register 30017 (smart load).
            v = (words[1] << 16) | words[0]
            if v >= 0x80000000:
                v -= 0x100000000
        else:
            v = (words[0] << 16) | words[1]
            if dtype == "I32" and v >= 0x80000000:
                v -= 0x100000000
    else:
        raise ValueError(f"unknown dtype {dtype!r}")
    if scale == 1.0:
        return v
    return v / scale

def decode_ascii_string(words, byte_swap=True) -> str:
    """Decode a byte-swapped ASCII string from a list of 16-bit words.

    Returns the longest run of printable characters; ``""`` if none.
    """
    parts = []
    for w in words:
        if byte_swap:
            hi, lo = w & 0xFF, (w >> 8) & 0xFF
        else:
            hi, lo = (w >> 8) & 0xFF, w & 0xFF
        for c in (hi, lo):
            parts.append(chr(c) if 32 <= c < 127 else ".")
    text = "".join(parts)
    runs = [run for run in text.split(".") if run]
    return max(runs, key=len) if runs else ""


__all__ = ["decode_words", "decode_ascii_string", "WSIZE"]
