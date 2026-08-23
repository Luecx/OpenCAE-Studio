"""Creates Part entities for the public :class:`opencae.api.Model` facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opencae.model.entities import Part

if TYPE_CHECKING:
    from .model import Model


def create_part(
    model: "Model",
    name: str,
    *,
    source_type: str = "Manual",
) -> Part:
    """Create a Part, attach it to the project, and refresh ownership indexes."""
    part = Part(name=name, source_type=source_type)
    model.project.parts.append(part)

    # Direct authoring mutations bypass ProjectStore, so the model facade owns
    # the index refresh at its mutation boundary.
    model._refresh()
    return part
