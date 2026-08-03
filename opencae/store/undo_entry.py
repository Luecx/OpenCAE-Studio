from dataclasses import dataclass

from .commands import ProjectCommand


@dataclass
class UndoEntry:
    description: str
    command: ProjectCommand
    active_before: str | None = None
    active_after: str | None = None
    selected_before: str | None = None
    selected_after: str | None = None
