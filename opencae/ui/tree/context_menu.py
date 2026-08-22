"""Builds tree context menus exclusively from centrally registered actions."""

from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QMenu

from opencae.ui.actions.ids import A
from .context_rules import available
from .tree_roles import ENTITY_ROLE, KIND_ROLE

VISIBILITY_KINDS = {
    "datum_point",
    "datum_vector",
    "datum_plane",
    "coordinate_system",
    "asm_coordinate_system",
    "reference_point",
    "asm_reference_point",
    "orientation",
    "support",
    "load",
    "constraint",
}

MAP = {
    "geometry_feature": (A.EDIT_SELECTED, A.SUPPRESS_FEATURE, A.REBUILD_GEOMETRY, A.DELETE_SELECTED),
    "seed": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "element_control": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "element_definition": (A.ELEMENT_CONTROLS,),
    "instance": (A.EDIT_SELECTED, A.TRANSFORM_INSTANCE, A.SUPPRESS_INSTANCE, A.DELETE_SELECTED),
    "support": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "load": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "material": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "field_definition": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "profile": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "section": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "parts": (A.NEW_PART,),
    "part": (A.DUPLICATE_PART, A.IMPORT_GEOMETRY, A.PARTITION, A.REBUILD_GEOMETRY, A.DEFAULT_SEED, A.GENERATE_MESH, A.DELETE_SELECTED),
    "geometry": (A.IMPORT_GEOMETRY, A.PARTITION, A.REBUILD_GEOMETRY),
    "mesh": (A.DEFAULT_SEED, A.EDGE_SEED, A.ELEMENT_CONTROLS, A.MESH_SETTINGS, A.GENERATE_MESH, A.CLEAR_MESH),
    "elements": (A.ELEMENT_CONTROLS,),
    "regions": (A.NODE_SET, A.ELEMENT_SET, A.SURFACE),
    "region": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "node_sets": (A.NODE_SET,),
    "element_sets": (A.ELEMENT_SET,),
    "surfaces": (A.SURFACE,),
    "coordinate_systems": (A.PART_CSYS,),
    "reference_points": (A.PART_RP,),
    "section_assignments": (A.SECTION_ASSIGNMENT,),
    "instances": (A.ADD_INSTANCE, A.DUPLICATE_INSTANCE),
    "asm_regions": (A.ASM_NODE_SET, A.ASM_ELEMENT_SET, A.ASM_SURFACE),
    "asm_region": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "asm_node_sets": (A.ASM_NODE_SET,),
    "asm_element_sets": (A.ASM_ELEMENT_SET,),
    "asm_surfaces": (A.ASM_SURFACE,),
    "asm_coordinate_systems": (A.ASM_CSYS,),
    "asm_reference_points": (A.ASM_RP,),
    "constraints": (A.CONSTRAINT_KINEMATIC, A.CONSTRAINT_DISTRIBUTING, A.CONSTRAINT_TIE, A.CONSTRAINT_RIGID, A.CONSTRAINT_EQUATION, A.CONSTRAINT_MPC),
    "constraint": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "supports": (A.FIXED, A.DISPLACEMENT, A.SYMMETRY),
    "loads": (A.CLOAD, A.DLOAD, A.PRESSURE, A.VLOAD, A.INERTIA_LOAD, A.TEMPERATURE),
    "materials": (A.MATERIAL,),
    "fields": (A.FIELD,),
    "profiles": (A.PROFILE_RECTANGLE, A.PROFILE_BOX, A.PROFILE_PIPE, A.PROFILE_I, A.PROFILE_CHANNEL, A.PROFILE_GENERAL, A.PROFILE_GRAPH),
    "sections": (A.SECTION_SOLID, A.SECTION_SHELL, A.SECTION_BEAM, A.SECTION_TRUSS),
    "steps": (A.STEP_LINEAR, A.STEP_NONLINEAR, A.STEP_MODAL, A.STEP_BUCKLING, A.STEP_TRANSIENT, A.REORDER_STEPS, A.STEP_MATRIX),
    "analysis_step": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "analysis_step_reference": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "analyses": (A.ANALYSIS_NEW,),
    "analysis": (
        A.ANALYSIS_NEW,
        A.ANALYSIS_EDIT,
        A.SOLVER_SETTINGS,
        A.VALIDATE,
        A.PREVIEW_DECK,
        A.WRITE_DECK,
        A.ANALYSIS_RUN,
        A.DELETE_SELECTED,
    ),
    "studies": (A.STUDY_NEW_TOPOLOGY,),
    "study": (
        A.STUDY_NEW_TOPOLOGY,
        A.STUDY_EDIT,
        A.OPT_RESPONSE,
        A.OPT_OBJECTIVE,
        A.OPT_CONSTRAINT,
        A.OPT_FILTER,
        A.OPT_SYMMETRY,
        A.OPT_CONTROLS,
        A.STUDY_VALIDATE,
        A.STUDY_RUN,
        A.DELETE_SELECTED,
    ),
    "topology_optimization": (
        A.STUDY_NEW_TOPOLOGY,
        A.STUDY_EDIT,
        A.OPT_RESPONSE,
        A.OPT_OBJECTIVE,
        A.OPT_CONSTRAINT,
        A.OPT_FILTER,
        A.OPT_SYMMETRY,
        A.OPT_CONTROLS,
        A.STUDY_VALIDATE,
        A.STUDY_RUN,
        A.DELETE_SELECTED,
    ),
    "study_responses": (A.OPT_RESPONSE,),
    "study_response": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "optimization_response": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "study_objectives": (A.OPT_OBJECTIVE,),
    "study_objective": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "optimization_objective": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "study_constraints": (A.OPT_CONSTRAINT,),
    "study_constraint": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "optimization_constraint": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "study_filters": (A.OPT_FILTER,),
    "study_filter": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "topology_filter_settings": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "study_symmetries": (A.OPT_SYMMETRY,),
    "study_symmetry": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "topology_symmetry": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "study_controls": (A.OPT_CONTROLS,),
    "study_control": (A.EDIT_SELECTED, A.DELETE_SELECTED),
    "topology_controls": (A.EDIT_SELECTED, A.DELETE_SELECTED),
}


def _menu_action(menu, source, enabled):
    """Create a menu-local action without changing the shared QAction state."""

    action = QAction(source.icon(), source.text(), menu)
    action.setEnabled(bool(enabled and source.isEnabled()))
    action.setToolTip(source.toolTip())
    action.setStatusTip(source.statusTip())
    action.triggered.connect(
        lambda _checked=False, shared=source: shared.trigger()
    )
    return action


def show_context_menu(view, pos, index, actions, store, visibility=None):
    kind = index.data(KIND_ROLE) if index.isValid() else None
    entity = index.data(ENTITY_ROLE) if index.isValid() else None
    ids = tuple(MAP.get(kind, ()))
    can_toggle = bool(
        visibility is not None
        and entity is not None
        and kind in VISIBILITY_KINDS
    )
    if not ids and not can_toggle:
        return
    menu = QMenu(view)
    if can_toggle:
        currently_visible = visibility.is_entity_visible(entity)
        toggle = menu.addAction("Hide" if currently_visible else "Show")
        toggle.setToolTip(
            "Hide this object in the viewport"
            if currently_visible
            else "Show this object in the viewport"
        )
        toggle.triggered.connect(
            lambda _checked=False, value=entity, visible=currently_visible: visibility.set_entity_visible(
                value,
                not visible,
            )
        )
        if ids:
            menu.addSeparator()
    for action_id in ids:
        source = actions.get(action_id)
        menu.addAction(
            _menu_action(
                menu,
                source,
                available(action_id, store, kind),
            )
        )
    menu.exec(view.viewport().mapToGlobal(pos))
