"""Compatibility name for the canonical OpenCAE form select."""

from opencae.ui.primitives.selects import SelectForm


class ChevronComboBox(SelectForm):
    """Backward-compatible public name backed by the canonical select primitive."""


__all__ = ["ChevronComboBox"]
