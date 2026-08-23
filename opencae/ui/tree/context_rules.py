"""Context-sensitive availability checks shared by tree context menus."""

from opencae.model.selection import ViewportSelection
from opencae.ui.actions.ids import A


def available(action_id, store, kind):
    """Return whether one action is valid for the current model/tree context."""
    project = store.project
    part = store.active_part()
    has_geometry = bool(part and part.geometry)
    has_mesh = bool(
        part and (part.mesh.node_count or part.mesh.element_definitions)
    )
    has_assembly = bool(project.assembly.instances)

    if action_id == A.DUPLICATE_PART:
        return part is not None
    if action_id in {
        A.PARTITION, A.REBUILD_GEOMETRY, A.SUPPRESS_FEATURE, A.DEFAULT_SEED,
        A.EDGE_SEED, A.MESH_SETTINGS, A.NODE_SET, A.ELEMENT_SET, A.SURFACE,
        A.PART_CSYS, A.PART_RP, A.SECTION_ASSIGNMENT,
    }:
        return has_geometry
    if action_id == A.GENERATE_MESH:
        return has_geometry and bool(part.mesh.seeds)
    if action_id in {A.CLEAR_MESH, A.ELEMENT_CONTROLS}:
        return has_mesh
    if action_id == A.ADD_INSTANCE:
        return bool(project.parts)
    if action_id in {
        A.DUPLICATE_INSTANCE, A.TRANSFORM_INSTANCE, A.SUPPRESS_INSTANCE,
    }:
        return has_assembly
    if action_id in {
        A.FIXED, A.DISPLACEMENT, A.SYMMETRY, A.CLOAD, A.DLOAD, A.PRESSURE,
        A.VLOAD, A.INERTIA_LOAD, A.TEMPERATURE, A.STEP_LINEAR,
        A.STEP_NONLINEAR, A.STEP_MODAL, A.STEP_BUCKLING, A.STEP_TRANSIENT,
    }:
        return has_assembly
    if action_id == A.ANALYSIS_NEW:
        return bool(project.steps)
    if action_id in {
        A.ANALYSIS_EDIT, A.VALIDATE, A.PREVIEW_DECK,
        A.WRITE_DECK, A.ANALYSIS_RUN,
    }:
        return bool(project.analyses) and has_assembly
    if action_id == A.STUDY_NEW_TOPOLOGY:
        return bool(project.analyses) and has_assembly
    if action_id in {
        A.STUDY_EDIT, A.STUDY_VALIDATE, A.STUDY_RUN, A.OPT_RESPONSE,
        A.OPT_OBJECTIVE, A.OPT_CONSTRAINT, A.OPT_FILTER,
        A.OPT_SYMMETRY, A.OPT_CONTROLS,
    }:
        return bool(project.studies)
    if action_id in {A.DELETE_SELECTED, A.EDIT_SELECTED}:
        return store.selection is not None and not isinstance(
            store.selection, ViewportSelection
        )
    return True
