from opencae.model.element_catalog import CATALOG
from opencae.model.entities.mesh import ElementTopology
from opencae.model.selection import (
    GeometryOperand,
    MeshElementOperand,
    MeshFacetOperand,
    NamedRegionOperand,
    RegionDefinition,
    WholeModelOperand,
)
from .element_records import records


def region_families(project, part, definition):
    """Infer compatible section families without materializing a region.

    Only direct mesh selections provide a definitive element family without
    projecting CAD topology onto the mesh.  Geometry-backed targets therefore
    remain intentionally unclassified in dialogs; their actual element family
    is checked when the deck materializes the region.
    """

    elements = records(part.mesh)
    families = set()

    def walk(value, stack):
        for item in RegionDefinition.from_values(value).items:
            operand = item.operand
            if isinstance(operand, NamedRegionOperand):
                region = project.try_resolve(operand.region_ref)
                if region is not None and region.id not in stack:
                    walk(region.definition, {*stack, region.id})
                continue
            if isinstance(operand, GeometryOperand):
                # A CAD face can bound a solid element just as easily as it can
                # represent a shell.  Inferring a section family from topology
                # dimension alone would be incorrect and would reintroduce
                # premature geometry-to-mesh projection.
                continue
            if isinstance(operand, (MeshElementOperand, MeshFacetOperand)):
                element = elements.get(int(operand.element_id))
                if element is not None:
                    families.add(_family(element))
                continue
            if isinstance(operand, WholeModelOperand):
                families.update(_family(element) for element in elements.values())

    walk(definition, set())
    return families


def compatible_sections(project, part, definition):
    families = region_families(project, part, definition)
    return [item for item in project.sections if not families or item.section_type in families]


def compatible_section_names(project, part, definition):
    return [item.name for item in compatible_sections(project, part, definition)]


def _family(element):
    if element.topology == ElementTopology.LINE:
        return "Beam" if element.formulation == "Beam" else "Truss"
    return "Shell" if CATALOG[element.topology].dimension == 2 else "Solid"
