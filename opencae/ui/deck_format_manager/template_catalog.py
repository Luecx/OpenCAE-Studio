"""Assemble focused record-template catalogs for the deck-format manager."""

from __future__ import annotations

from .analysis_template_catalog import TEMPLATE_SPECS as ANALYSIS_SPECS
from .constraint_template_catalog import TEMPLATE_SPECS as CONSTRAINT_SPECS
from .element_type_catalog import element_template_specs
from .field_template_catalog import TEMPLATE_SPECS as FIELD_SPECS
from .load_template_catalog import TEMPLATE_SPECS as LOAD_SPECS
from .material_template_catalog import TEMPLATE_SPECS as MATERIAL_SPECS
from .mesh_template_catalog import TEMPLATE_SPECS as MESH_SPECS
from .profile_record_catalog import profile_template_specs
from .section_template_catalog import TEMPLATE_SPECS as SECTION_SPECS


def _merge_catalogs(*catalogs: dict[str, dict]) -> dict[str, dict]:
    """Merge record catalogs while rejecting accidental duplicate stable keys."""
    result: dict[str, dict] = {}
    for catalog in catalogs:
        overlap = result.keys() & catalog.keys()
        if overlap:
            raise ValueError(f"Duplicate deck template keys: {sorted(overlap)}")
        result.update(catalog)
    return result


TEMPLATE_SPECS = _merge_catalogs(
    MESH_SPECS,
    element_template_specs(),
    MATERIAL_SPECS,
    SECTION_SPECS,
    profile_template_specs(),
    FIELD_SPECS,
    LOAD_SPECS,
    CONSTRAINT_SPECS,
    ANALYSIS_SPECS,
)


def template_command_names() -> frozenset[str]:
    """Return every solver keyword represented by an explicit editor template."""
    commands: set[str] = set()
    for spec in TEMPLATE_SPECS.values():
        commands.update(str(command) for command in spec.get("commands", ()))
    return frozenset(commands)


__all__ = ["TEMPLATE_SPECS", "template_command_names"]
