"""In-memory raw-word cache with typed decoding."""
from __future__ import annotations

from .decode import decode_words
from .registers import REGISTERS_BY_ADDR, WSIZE


class RegisterCache:
    """Stores raw address -> 16-bit word, decodes typed values on demand."""

    def __init__(self, by_key, by_addr):
        self._by_key = by_key
        self._by_addr = by_addr
        self._raw: dict[int, int] = {}

    def update(self, raw: dict) -> None:
        self._raw.update(raw)

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
        return decode_words(words, reg.dtype, reg.scale)
