"""Compatibility layer for the canonical label-above-control form field."""

from __future__ import annotations

from PyQt6.QtWidgets import QWidget

from opencae.ui.composites import FormField


class FieldBlock(FormField):
    """Backward-compatible name for the canonical form field composite."""


def field_block(label_text: str, control: QWidget, parent=None) -> FieldBlock:
    """Return the canonical reusable field block for one dialog control."""
    return FieldBlock(label_text, control, parent)
