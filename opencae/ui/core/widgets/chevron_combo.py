"""Compatibility name for the canonical OpenCAE choice input."""

from opencae.ui.primitives.inputs import ChoiceInput


class ChevronComboBox(ChoiceInput):
    """Backward-compatible alias preserving the existing public widget name."""


__all__ = ["ChevronComboBox"]
