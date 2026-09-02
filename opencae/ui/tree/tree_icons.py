from opencae.ui.core.icon_factory import IconKind, make_icon

_KIND_ICONS={
    "parts":IconKind.PART,"part":IconKind.PART,"geometry":IconKind.PARTITION,"geometry_feature":IconKind.PARTITION,
    "mesh":IconKind.MESH,"seed":IconKind.SEED,"element_control":IconKind.ELEMENT_CONTROLS,"nodes":IconKind.NODE_SET,
    "elements":IconKind.ELEMENT,"element_category":IconKind.ELEMENT,"element_definition":IconKind.ELEMENT,
    "regions":IconKind.NODE_SET,"region":IconKind.NODE_SET,"node_sets":IconKind.NODE_SET,"node_set":IconKind.NODE_SET,"element_sets":IconKind.ELEMENT_SET,"element_set":IconKind.ELEMENT_SET,
    "surfaces":IconKind.SURFACE,"surface":IconKind.SURFACE,"coordinate_systems":IconKind.CSYS,"coordinate_system":IconKind.CSYS,
    "reference_points":IconKind.RP,"reference_point":IconKind.RP,"datums":IconKind.CSYS,"datum_point":IconKind.RP,"datum_vector":IconKind.CSYS,"datum_plane":IconKind.SURFACE,"section_assignments":IconKind.ASSIGN,"section_assignment":IconKind.ASSIGN,
    "assembly":IconKind.INSTANCE,"asm_regions":IconKind.NODE_SET,"asm_region":IconKind.NODE_SET,"instances":IconKind.INSTANCE,"instance":IconKind.INSTANCE,"asm_node_sets":IconKind.NODE_SET,
    "asm_node_set":IconKind.NODE_SET,"asm_element_sets":IconKind.ELEMENT_SET,"asm_element_set":IconKind.ELEMENT_SET,
    "asm_surfaces":IconKind.SURFACE,"asm_surface":IconKind.SURFACE,"asm_coordinate_systems":IconKind.CSYS,
    "asm_coordinate_system":IconKind.CSYS,"asm_reference_points":IconKind.RP,"asm_reference_point":IconKind.RP,
    "constraints":IconKind.CONSTRAINT,"constraint":IconKind.CONSTRAINT,"supports":IconKind.SUPPORT,"support":IconKind.SUPPORT,
    "loads":IconKind.LOAD,"load":IconKind.LOAD,"amplitudes":IconKind.FIELD,"amplitude":IconKind.FIELD,
    "materials":IconKind.MATERIAL,"material":IconKind.MATERIAL,
    "sections":IconKind.SECTION,"section":IconKind.SECTION,"fields":IconKind.FIELD,"field_definition":IconKind.FIELD,
    "profiles":IconKind.PROFILE,"profile":IconKind.PROFILE,"steps":IconKind.ANALYSIS,"analysis_step":IconKind.ANALYSIS,
    "optimizations":IconKind.CONTOUR,"topology_optimization":IconKind.CONTOUR,
    "optimization_responses":IconKind.FIELD,"optimization_response":IconKind.FIELD,
    "optimization_objectives":IconKind.CONTOUR,"optimization_objective":IconKind.CONTOUR,
    "optimization_constraints":IconKind.CONSTRAINT,"optimization_constraint":IconKind.CONSTRAINT,
    "topology_filters":IconKind.RANGE,"topology_filter_settings":IconKind.RANGE,
    "topology_symmetries":IconKind.CSYS,"topology_symmetry":IconKind.CSYS,
    "topology_controls":IconKind.SETTINGS,
    "optimization_runs":IconKind.RUN,"optimization_run":IconKind.RUN,
    "optimization_iteration":IconKind.RESULT_FRAME,
}


def icon_for(kind):return make_icon(_KIND_ICONS.get(kind,IconKind.INFO),18)
