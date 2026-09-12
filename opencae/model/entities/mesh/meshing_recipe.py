"""Persistent meshing intent independent from finite-element mesh data."""

from dataclasses import dataclass, field

from ...core import register_model_type
from .element_control import ElementControl
from .mesh_settings import MeshSettings
from .seed import Seed


@register_model_type("meshing_recipe")
@dataclass
class MeshingRecipe:
    """Own user-authored settings that can generate or regenerate a mesh."""

    settings: MeshSettings = field(
        default_factory=MeshSettings,
        metadata={"project_index": False},
    )
    seeds: list[Seed] = field(default_factory=list)
    element_controls: list[ElementControl] = field(default_factory=list)
