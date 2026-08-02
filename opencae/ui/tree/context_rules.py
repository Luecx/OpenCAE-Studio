from opencae.ui.actions.ids import A


def available(action_id,store,kind):
    project=store.project; part=store.active_part(); has_geometry=bool(part and part.geometry); has_mesh=bool(part and (part.mesh.node_count or part.mesh.elements)); has_assembly=bool(project.assembly.instances)
    if action_id==A.DUPLICATE_PART:return part is not None
    if action_id in {A.PARTITION,A.REBUILD_GEOMETRY,A.SUPPRESS_FEATURE,A.DEFAULT_SEED,A.EDGE_SEED,A.MESH_CONTROL,A.MESH_SETTINGS,A.NODE_SET,A.ELEMENT_SET,A.SURFACE,A.PART_CSYS,A.PART_RP,A.SECTION_ASSIGNMENT}:return has_geometry
    if action_id==A.GENERATE_MESH:return has_geometry and bool(part.mesh.seeds)
    if action_id in {A.CLEAR_MESH,A.ELEMENT_CONTROLS}:return has_mesh
    if action_id==A.ADD_INSTANCE:return bool(project.parts)
    if action_id in {A.DUPLICATE_INSTANCE,A.TRANSFORM_INSTANCE,A.SUPPRESS_INSTANCE}:return has_assembly
    if action_id in {A.FIXED,A.DISPLACEMENT,A.SYMMETRY,A.CLOAD,A.DLOAD,A.PRESSURE,A.VLOAD,A.INERTIA_LOAD,A.TEMPERATURE,A.STEP_LINEAR,A.STEP_NONLINEAR,A.STEP_MODAL,A.STEP_BUCKLING,A.STEP_TRANSIENT}:return has_assembly
    if action_id in {A.PREVIEW_DECK,A.WRITE_DECK,A.RUN}:return bool(project.analyses) and has_assembly
    if action_id in {A.DELETE_SELECTED,A.EDIT_SELECTED}:return store.selection is not None and not isinstance(store.selection,dict)
    return True
