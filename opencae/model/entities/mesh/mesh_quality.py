"""Derived finite-element quality summary."""

from dataclasses import dataclass

from ...core import register_model_type


@register_model_type("mesh_quality_summary")
@dataclass
class MeshQualitySummary:
    """Cache aggregate quality metrics without owning FE data."""

    minimum: float | None = None
    mean: float | None = None
    invalid_element_ids: tuple[int, ...] = ()
    inverted_element_ids: tuple[int, ...] = ()
    degenerate_element_ids: tuple[int, ...] = ()

    def invalidate(self) -> None:
        self.minimum = None
        self.mean = None
        self.invalid_element_ids = ()
        self.inverted_element_ids = ()
        self.degenerate_element_ids = ()
