from PyQt6.QtWidgets import QMenu
from opencae.ui.actions.ids import A
from .context_rules import available

MAP={
 "geometry_feature":(A.EDIT_SELECTED,A.SUPPRESS_FEATURE,A.REBUILD_GEOMETRY,A.DELETE_SELECTED),"seed":(A.EDIT_SELECTED,A.DELETE_SELECTED),"element_control":(A.EDIT_SELECTED,A.DELETE_SELECTED),"element_definition":(A.ELEMENT_CONTROLS,),"instance":(A.EDIT_SELECTED,A.TRANSFORM_INSTANCE,A.SUPPRESS_INSTANCE,A.DELETE_SELECTED),
 "support":(A.EDIT_SELECTED,A.DELETE_SELECTED),"load":(A.EDIT_SELECTED,A.DELETE_SELECTED),"material":(A.EDIT_SELECTED,A.DELETE_SELECTED),"field_definition":(A.EDIT_SELECTED,A.DELETE_SELECTED),"profile":(A.EDIT_SELECTED,A.DELETE_SELECTED),"section":(A.EDIT_SELECTED,A.DELETE_SELECTED),"analysis_step":(A.EDIT_SELECTED,A.DELETE_SELECTED),
 "parts":(A.NEW_PART,),"part":(A.DUPLICATE_PART,A.IMPORT_GEOMETRY,A.PARTITION,A.REBUILD_GEOMETRY,A.DEFAULT_SEED,A.GENERATE_MESH,A.DELETE_SELECTED),"geometry":(A.IMPORT_GEOMETRY,A.PARTITION,A.REBUILD_GEOMETRY),
 "mesh":(A.DEFAULT_SEED,A.EDGE_SEED,A.ELEMENT_CONTROLS,A.MESH_SETTINGS,A.GENERATE_MESH,A.CLEAR_MESH),"elements":(A.ELEMENT_CONTROLS,),
 "regions":(A.NODE_SET,A.ELEMENT_SET,A.SURFACE),"region":(A.EDIT_SELECTED,A.DELETE_SELECTED),"node_sets":(A.NODE_SET,),"element_sets":(A.ELEMENT_SET,),"surfaces":(A.SURFACE,),"coordinate_systems":(A.PART_CSYS,),"reference_points":(A.PART_RP,),"section_assignments":(A.SECTION_ASSIGNMENT,),
 "instances":(A.ADD_INSTANCE,A.DUPLICATE_INSTANCE),"asm_regions":(A.ASM_NODE_SET,A.ASM_ELEMENT_SET,A.ASM_SURFACE),"asm_region":(A.EDIT_SELECTED,A.DELETE_SELECTED),"asm_node_sets":(A.ASM_NODE_SET,),"asm_element_sets":(A.ASM_ELEMENT_SET,),"asm_surfaces":(A.ASM_SURFACE,),"asm_coordinate_systems":(A.ASM_CSYS,),"asm_reference_points":(A.ASM_RP,),"constraints":(A.CONSTRAINT_KINEMATIC,A.CONSTRAINT_DISTRIBUTING,A.CONSTRAINT_TIE,A.CONSTRAINT_RIGID,A.CONSTRAINT_EQUATION,A.CONSTRAINT_MPC),
 "supports":(A.FIXED,A.DISPLACEMENT,A.SYMMETRY),"loads":(A.CLOAD,A.DLOAD,A.PRESSURE,A.VLOAD,A.INERTIA_LOAD,A.TEMPERATURE),
 "materials":(A.MATERIAL,),"fields":(A.FIELD,),
 "profiles":(A.PROFILE_RECTANGLE,A.PROFILE_BOX,A.PROFILE_PIPE,A.PROFILE_I,A.PROFILE_CHANNEL,A.PROFILE_GENERAL,A.PROFILE_GRAPH),
 "sections":(A.SECTION_SOLID,A.SECTION_SHELL,A.SECTION_BEAM,A.SECTION_TRUSS),
 "steps":(A.STEP_LINEAR,A.STEP_NONLINEAR,A.STEP_MODAL,A.STEP_BUCKLING,A.STEP_TRANSIENT,A.REORDER_STEPS,A.STEP_MATRIX),
}


def show_context_menu(view,pos,kind,actions,store):
    ids=[action_id for action_id in MAP.get(kind,()) if available(action_id,store,kind) and actions.get(action_id).isEnabled()]
    if not ids:return
    menu=QMenu(view)
    for action_id in ids:menu.addAction(actions.get(action_id))
    menu.exec(view.viewport().mapToGlobal(pos))
