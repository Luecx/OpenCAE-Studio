"""Assemble the deck-format editor catalog and live-preview helpers."""

from __future__ import annotations

from copy import deepcopy

from .format_capabilities import ABAQUS_FAMILY, ALL_FORMATS, FEMASTER_ONLY
from .template_catalog import TEMPLATE_SPECS
from .template_language import loop_from_spec, render_template
from .tree_catalog import TREE_SPEC as _RAW_TREE_SPEC


GLOBAL_PAGES = {
    "general.formatting": "Formatting",
    "general.comments": "Comments",
    "general.output": "Output Style",
}

# The tree is organized by OpenCAE semantics. Format support belongs here rather
# than in the FEMaster-originating catalog: a record stays enabled whenever the
# target dialect has a native equivalent, even when the keyword itself differs.
_NATIVE_SUPPORT = {
    "mesh.nodes": ALL_FORMATS,
    "node_sets": ALL_FORMATS,
    "element_sets": ALL_FORMATS,
    "surfaces.definition": ALL_FORMATS,
    "surfaces.set": FEMASTER_ONLY,
    "materials.header": ALL_FORMATS,
    "materials.elastic.isotropic": ALL_FORMATS,
    "materials.elastic.generalised_isotropic": FEMASTER_ONLY,
    "materials.elastic.engineering_constants": ALL_FORMATS,
    "materials.elastic.orthotropic_stiffness": ALL_FORMATS,
    "materials.hyperelastic.neo_hooke": ALL_FORMATS,
    "materials.density": ALL_FORMATS,
    "materials.thermal_expansion": ALL_FORMATS,
    "materials.plasticity": ABAQUS_FAMILY,
    "sections.solid": ALL_FORMATS,
    "sections.shell.integrated": ALL_FORMATS,
    "sections.shell.abd": FEMASTER_ONLY,
    "sections.beam": ALL_FORMATS,
    "sections.truss": ALL_FORMATS,
    "coordinate_systems.rectangular": ALL_FORMATS,
    "coordinate_systems.cylindrical": ALL_FORMATS,
    "reference_points": ALL_FORMATS,
    "constraints.kinematic.surface": ALL_FORMATS,
    "constraints.distributing.surface": ALL_FORMATS,
    "constraints.tie": ALL_FORMATS,
    "constraints.rigid": ALL_FORMATS,
    "constraints.equation": ALL_FORMATS,
    "boundary_conditions.fixed": ALL_FORMATS,
    "boundary_conditions.displacement": ALL_FORMATS,
    "boundary_conditions.symmetry": ALL_FORMATS,
    "loads.amplitude": ALL_FORMATS,
    "loads.concentrated": ALL_FORMATS,
    "loads.distributed": ("FEMaster", "Abaqus"),
    "loads.pressure": ALL_FORMATS,
    "loads.volume": ("FEMaster", "Abaqus"),
    "loads.inertia": ("FEMaster", "Abaqus"),
    "loads.temperature": ALL_FORMATS,
    "analysis.loadcases.linear_static": ALL_FORMATS,
    "analysis.loadcases.nonlinear_static": ALL_FORMATS,
    "analysis.loadcases.linear_buckling": ALL_FORMATS,
    "analysis.loadcases.topology_static": FEMASTER_ONLY,
    "analysis.loadcases.eigenfrequency": ALL_FORMATS,
    "analysis.loadcases.linear_transient": ALL_FORMATS,
    "analysis.loadcases.linear_harmonic": FEMASTER_ONLY,
    "analysis.end": ALL_FORMATS,
}


def _native_tree(nodes: tuple[dict, ...]) -> tuple[dict, ...]:
    """Apply native support overrides recursively without mutating source specs."""
    result = []
    for source in nodes:
        node = deepcopy(source)
        key = str(node.get("key", ""))
        if key in _NATIVE_SUPPORT:
            node["supported_formats"] = tuple(_NATIVE_SUPPORT[key])
        children = tuple(node.get("children", ()))
        if children:
            node["children"] = _native_tree(children)
        result.append(node)
    return tuple(result)


TREE_SPEC = _native_tree(_RAW_TREE_SPEC)


def template_spec(
    key: str,
    _label: str = "",
    format_name: str = "FEMaster",
) -> dict:
    """Return the concrete template specification for one format and tree leaf."""
    try:
        result = deepcopy(TEMPLATE_SPECS[key])
    except KeyError as exc:
        raise KeyError(f"No deck template is registered for '{key}'") from exc

    variants = dict(result.pop("formats", {}))
    override = variants.get(str(format_name))
    if isinstance(override, dict):
        result.update(deepcopy(override))
    return result


def format_preview_value(value: object, float_format: str = ".6g") -> str:
    """Format floating-point examples while preserving identifiers and strings."""
    if isinstance(value, float):
        return format(value, float_format)
    return str(value)


def formatted_spec(spec: dict, float_format: str = ".6g") -> dict:
    """Return a preview-only copy with numeric examples formatted consistently."""
    result = deepcopy(spec)
    result["fields"] = tuple(
        (name, description, format_preview_value(example, float_format))
        for name, description, example in tuple(spec.get("fields", ()))
    )
    loops = []
    for loop in spec.get("loops", ()):
        item = deepcopy(loop)
        item["fields"] = tuple(
            (name, description, format_preview_value(example, float_format))
            for name, description, example in tuple(loop.get("fields", ()))
        )
        item["examples"] = tuple(
            {
                key: format_preview_value(value, float_format)
                for key, value in example.items()
            }
            for example in tuple(loop.get("examples", ()))
        )
        loops.append(item)
    result["loops"] = tuple(loops)
    return result


def render_preview(
    template: str,
    spec: dict,
    *,
    float_format: str = ".6g",
) -> str:
    """Render a representative block using the selected floating-point format."""
    preview = formatted_spec(spec, float_format)
    values = {
        name: example
        for name, _description, example in tuple(preview.get("fields", ()))
    }
    loops = tuple(loop_from_spec(item) for item in preview.get("loops", ()))
    return render_template(template, values, loops)


__all__ = [
    "GLOBAL_PAGES",
    "TREE_SPEC",
    "format_preview_value",
    "formatted_spec",
    "render_preview",
    "template_spec",
]
