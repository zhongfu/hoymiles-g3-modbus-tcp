"""In-memory raw-word cache with typed decoding."""
from __future__ import annotations

import time

from .decode import decode_words
from .registers import REGISTERS_BY_ADDR, WSIZE


class RegisterCache:
    """Stores raw address -> 16-bit word, decodes typed values on demand."""
    def __init__(self, by_key, by_addr):
        self._by_key = by_key
        self._by_addr = by_addr
        self._raw: dict[int, int] = {}
        self._ts: dict[int, float] = {}  # addr -> wall-clock time of last good read

    def update(self, raw: dict) -> None:
        now = time.time()
        for addr, value in raw.items():
            if value is not None:
                self._raw[addr] = value
                self._ts[addr] = now

    def last_update(self, reg) -> float | None:
        """Wall-clock time of the last successful read of ``reg`` (derived: components).

        Returns ``None`` if the register (or any of its source components, for
        derived totals) has never been read successfully.
        """
        if reg.source:
            stamps = [
                self._ts.get(self._by_key[key].addr)
                for key in reg.source
            ]
            if any(t is None for t in stamps):
                return None
            # A derived value is only as fresh as its oldest component.
            return min(stamps)
        return self._ts.get(reg.addr)

    def raw_addr(self, addr: int) -> int | None:
        return self._raw.get(addr)

    def words(self, reg) -> list:
        n = WSIZE[reg.dtype]
        return [self._raw.get(reg.addr + i) for i in range(n)]

    def value(self, reg):
        if reg.source:
            total = 0
            for key in reg.source:
                comp = self._by_key[key]
                cv = self.value(comp)
                if cv is None:
                    return None
                total += cv
            return total
        words = self.words(reg)
        if any(w is None for w in words):
            return None
        v = decode_words(words, reg.dtype, reg.scale)
        if reg.enum is not None and isinstance(v, int):
            return reg.enum.get(v, v)
        if reg.bitmap is not None and isinstance(v, int):
            return [label for bit, label in sorted(reg.bitmap.items()) if v & (1 << bit)]
        return v
