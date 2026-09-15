"""Compatibility name for the canonical vertical form stack composite."""

from opencae.ui.composites import FieldStack as _FieldStack


class FieldStack(_FieldStack):
    """Backward-compatible template name for the reusable form stack."""


__all__ = ["FieldStack"]
