from __future__ import annotations

import re


def safe_solver_name(value) -> str:
    text = re.sub(r"[^A-Za-z0-9_]", "_", str(value or "ENTITY")).upper().strip("_")
    return text or "ENTITY"


class ExportNameRegistry:
    def __init__(self):
        self._by_key: dict[object, str] = {}
        self._used: dict[str, object] = {}

    def register(self, key: object, proposed: str) -> str:
        if key in self._by_key: return self._by_key[key]
        base = safe_solver_name(proposed); name = base; index = 2
        while name in self._used and self._used[name] != key:
            name = f"{base}_{index}"; index += 1
        self._by_key[key] = name; self._used[name] = key
        return name

    def get(self, key: object, default: str = "") -> str: return self._by_key.get(key, default)
