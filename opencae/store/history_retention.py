"""Defines bounded retention policy for reversible ProjectStore history."""

from __future__ import annotations

from .undo_entry import UndoEntry


MAX_UNDO_ENTRIES = 200
MAX_LARGE_PAYLOAD_ENTRIES = 2


def trim_undo_history(entries: list[UndoEntry]) -> None:
    """Discard the oldest undo prefix when history exceeds memory policy.

    Ordinary metadata/model edits keep a generous 200-step history. Commands
    that retain an inactive full mesh are capped at two entries, preventing
    repeated mesh generation or element conversion from pinning an unbounded
    number of 400k-element meshes in RAM. Trimming always removes an oldest
    prefix so the remaining undo chain stays contiguous and valid.
    """
    while len(entries) > MAX_UNDO_ENTRIES:
        entries.pop(0)

    large_count = sum(
        1
        for entry in entries
        if entry.command.retains_large_payload()
    )
    while large_count > MAX_LARGE_PAYLOAD_ENTRIES and entries:
        removed = entries.pop(0)
        if removed.command.retains_large_payload():
            large_count -= 1
