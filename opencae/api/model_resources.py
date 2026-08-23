"""Creates material and section resources for the public Model facade."""

from __future__ import annotations

from typing import TYPE_CHECKING

from opencae.model.entities import Material, Profile, Section
from opencae.model.entities.resources.material_behaviors import (
    DensityBehavior,
    IsotropicElasticity,
)

if TYPE_CHECKING:
    from .model import Model


def create_material(
    model: "Model",
    name: str,
    *,
    youngs_modulus: float | None = None,
    poisson_ratio: float | None = None,
    density: float | None = None,
) -> Material:
    """Create a material while enforcing complete elasticity parameters."""
    behaviors = []

    # E and nu form one constitutive law. Accepting only one would create a
    # material that looks valid in Python but cannot be exported consistently.
    if youngs_modulus is not None or poisson_ratio is not None:
        if youngs_modulus is None or poisson_ratio is None:
            raise ValueError(
                "youngs_modulus and poisson_ratio must be supplied together"
            )
        behaviors.append(
            IsotropicElasticity(
                youngs_modulus=float(youngs_modulus),
                poisson_ratio=float(poisson_ratio),
            )
        )

    if density is not None:
        behaviors.append(DensityBehavior(value=float(density)))

    material = Material(name=name, behaviors=behaviors)
    model.project.materials.append(material)
    model._refresh()
    return material


def create_section(
    model: "Model",
    name: str,
    *,
    material: Material | None = None,
    profile: Profile | None = None,
    section_type: str = "Solid",
    thickness: float = 0.0,
) -> Section:
    """Create a section whose public relationships are object references."""
    if material is not None:
        model._require_owned(material, Material)
    if profile is not None:
        model._require_owned(profile, Profile)

    section = Section(
        name=name,
        section_type=section_type,
        thickness=float(thickness),
    )

    # Object properties translate to stable EntityRef values internally. Public
    # callers therefore never need to construct ID/string references.
    section.material = material
    section.profile = profile

    model.project.sections.append(section)
    model._refresh()
    return section
