"""Byte pattern (AOB) support using the same syntax re4_tweaks uses.

Patterns look like: ``A1 ?? ?? ?? ?? B9 FF FF FF 7F 21 48 ?? A1``
where ``??`` (or ``?`` / ``**``) is a wildcard byte.
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence, Union


class Pattern:
    def __init__(self, text: str) -> None:
        tokens: List[Optional[int]] = []
        for part in text.split():
            if part in ("?", "??", "**"):
                tokens.append(None)
            else:
                if len(part) != 2:
                    raise ValueError(f"bad pattern token: {part!r}")
                tokens.append(int(part, 16))
        if not tokens:
            raise ValueError("empty pattern")
        self.tokens = tokens
        self.length = len(tokens)
        # Pre-compute a cheap pre-filter: the first concrete byte.
        self._first_index = next(i for i, t in enumerate(tokens) if t is not None)
        first = tokens[self._first_index]
        assert first is not None
        self._first_byte = bytes([first])

    def matches_at(self, data: Union[bytes, bytearray], offset: int) -> bool:
        for i, token in enumerate(self.tokens):
            if token is not None and data[offset + i] != token:
                return False
        return True

    def find_all(
        self,
        data: Union[bytes, bytearray],
        limit: Optional[int] = None,
    ) -> List[int]:
        hits: List[int] = []
        size = len(data)
        needle = self._first_byte
        search_from = 0
        while True:
            idx = data.find(needle, search_from)
            if idx < 0:
                break
            base = idx - self._first_index
            if base >= 0 and base + self.length <= size and self.matches_at(data, base):
                hits.append(base)
                if limit is not None and len(hits) >= limit:
                    break
            search_from = idx + 1
        return hits

    def find_first(self, data: Union[bytes, bytearray]) -> Optional[int]:
        hits = self.find_all(data, limit=1)
        return hits[0] if hits else None


def find_all(data: Union[bytes, bytearray], pattern: str, limit: Optional[int] = None) -> List[int]:
    return Pattern(pattern).find_all(data, limit=limit)


def find_first(data: Union[bytes, bytearray], pattern: str) -> Optional[int]:
    return Pattern(pattern).find_first(data)
