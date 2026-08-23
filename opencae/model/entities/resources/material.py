"""Defines material resources and their constitutive behavior collection."""

from dataclasses import dataclass, field

from ...core import Entity, register_model_type
from .material_behaviors import DensityBehavior, IsotropicElasticity, MaterialBehavior


@register_model_type("material")
@dataclass
class Material(Entity):
    """Material resource with behavior objects as its canonical properties."""

    behaviors: list[MaterialBehavior] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    density: float = 0.0
    youngs_modulus: float = 0.0
    poisson_ratio: float = 0.0

    def __post_init__(self):
        """Populate behavior objects from the current convenience scalar fields."""
        if not self.behaviors and (self.youngs_modulus or self.poisson_ratio):
            self.behaviors.append(
                IsotropicElasticity(
                    youngs_modulus=self.youngs_modulus,
                    poisson_ratio=self.poisson_ratio,
                )
            )
        if (
            not any(isinstance(item, DensityBehavior) for item in self.behaviors)
            and self.density
        ):
            self.behaviors.append(DensityBehavior(value=self.density))

    def write_abaqus(self, writer, context) -> None:
        """Write material behaviors in Abaqus syntax."""
        writer.line(f"*MATERIAL, NAME={self.name}")
        for behavior in self.behaviors:
            if isinstance(behavior, IsotropicElasticity):
                writer.line("*ELASTIC")
                writer.line(
                    f"{behavior.youngs_modulus}, {behavior.poisson_ratio}"
                )
            elif isinstance(behavior, DensityBehavior):
                writer.line("*DENSITY")
                writer.line(str(behavior.value))

    def write_femaster(self, writer, context) -> None:
        """Defer FEMaster material formatting to the exporter service."""
        return None
