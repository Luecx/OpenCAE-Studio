from opencae.ui.core.icon_factory import IconKind, make_icon

_KIND_ICONS={
    "parts":IconKind.PART,"part":IconKind.PART,"geometry":IconKind.PARTITION,"geometry_feature":IconKind.PARTITION,
    "mesh":IconKind.MESH,"seed":IconKind.SEED,"mesh_control":IconKind.MESH,"nodes":IconKind.NODE_SET,
    "elements":IconKind.ELEMENT,"element_category":IconKind.ELEMENT,"element_definition":IconKind.ELEMENT,
    "node_sets":IconKind.NODE_SET,"node_set":IconKind.NODE_SET,"element_sets":IconKind.ELEMENT_SET,"element_set":IconKind.ELEMENT_SET,
    "surfaces":IconKind.SURFACE,"surface":IconKind.SURFACE,"coordinate_systems":IconKind.CSYS,"coordinate_system":IconKind.CSYS,
    "reference_points":IconKind.RP,"reference_point":IconKind.RP,"datums":IconKind.CSYS,"datum_point":IconKind.RP,"datum_vector":IconKind.CSYS,"datum_plane":IconKind.SURFACE,"section_assignments":IconKind.ASSIGN,"section_assignment":IconKind.ASSIGN,
    "assembly":IconKind.INSTANCE,"instances":IconKind.INSTANCE,"instance":IconKind.INSTANCE,"asm_node_sets":IconKind.NODE_SET,
    "asm_node_set":IconKind.NODE_SET,"asm_element_sets":IconKind.ELEMENT_SET,"asm_element_set":IconKind.ELEMENT_SET,
    "asm_surfaces":IconKind.SURFACE,"asm_surface":IconKind.SURFACE,"asm_coordinate_systems":IconKind.CSYS,
    "asm_coordinate_system":IconKind.CSYS,"asm_reference_points":IconKind.RP,"asm_reference_point":IconKind.RP,
    "constraints":IconKind.CONSTRAINT,"constraint":IconKind.CONSTRAINT,"supports":IconKind.SUPPORT,"support":IconKind.SUPPORT,
    "loads":IconKind.LOAD,"load":IconKind.LOAD,"materials":IconKind.MATERIAL,"material":IconKind.MATERIAL,
    "sections":IconKind.SECTION,"section":IconKind.SECTION,"fields":IconKind.FIELD,"field_definition":IconKind.FIELD,
    "profiles":IconKind.PROFILE,"profile":IconKind.PROFILE,"steps":IconKind.ANALYSIS,"analysis_step":IconKind.ANALYSIS,
}


def icon_for(kind):return make_icon(_KIND_ICONS.get(kind,IconKind.INFO),18)
