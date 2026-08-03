from opencae.ui.actions.ids import A
from opencae.ui.actions.spec import ActionSpec
from opencae.ui.core.icon_factory import IconKind as I


def specs(c):
    return (
        ActionSpec(A.NEW_PART, "New Part", I.PART, c.part.new_part),
        ActionSpec(A.DUPLICATE_PART, "Duplicate Part", I.PART, c.part.duplicate_part),
        ActionSpec(A.IMPORT_GEOMETRY, "Import CAD", I.IMPORT, c.part.import_geometry),
        ActionSpec(A.IMPORT_MESH, "Import Mesh", I.MESH, c.part.import_mesh),
        ActionSpec(A.PARTITION, "Partition", I.PARTITION, c.part.partition),
        ActionSpec(A.REBUILD_GEOMETRY, "Rebuild", I.VALIDATE, c.part.rebuild_geometry),
        ActionSpec(A.SUPPRESS_FEATURE, "Suppress / Resume", I.DELETE, c.part.suppress_feature),
        ActionSpec(A.DEFAULT_SEED, "Seed Part", I.SEED, c.part.default_seed),
        ActionSpec(A.EDGE_SEED, "Seed Edges", I.SEED, c.part.edge_seed),
        ActionSpec(A.ELEMENT_CONTROLS, "Element Controls", I.ELEMENT_CONTROLS, c.part.element_controls),
        ActionSpec(A.MESH_SETTINGS, "Mesh Settings", I.SETTINGS, c.part.mesh_settings),
        ActionSpec(A.GENERATE_MESH, "Generate Mesh", I.MESH, c.part.generate_mesh),
        ActionSpec(A.CLEAR_MESH, "Clear Mesh", I.DELETE, c.part.clear_mesh),
        ActionSpec(A.NODE_SET, "Node Set", I.NODE_SET, c.part.node_set),
        ActionSpec(A.ELEMENT_SET, "Element Set", I.ELEMENT_SET, c.part.element_set),
        ActionSpec(A.SURFACE, "Surface", I.SURFACE, c.part.surface),
        ActionSpec(A.PART_CSYS, "Coordinate System", I.CSYS, c.part.coordinate_system),
        ActionSpec(A.PART_RP, "Reference Point", I.RP, c.part.reference_point),
        ActionSpec(A.DATUM_POINT, "Point", I.RP, c.part.datum_point),
        ActionSpec(A.DATUM_VECTOR, "Vector", I.CSYS, c.part.datum_vector),
        ActionSpec(A.DATUM_PLANE, "Plane", I.SURFACE, c.part.datum_plane),
        ActionSpec(A.SECTION_ASSIGNMENT, "Assign Section", I.ASSIGN, c.part.section_assignment),
    )
