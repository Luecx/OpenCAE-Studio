from dataclasses import dataclass
from .json_patch import Change

@dataclass
class UndoEntry:
    description: str
    patch: list[Change]
    active_before: str | None = None
    active_after: str | None = None
