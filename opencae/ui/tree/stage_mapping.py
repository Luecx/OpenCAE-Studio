MATERIAL_KINDS = {"materials", "material"}
SECTION_KINDS = {"sections", "section"}
PROFILE_KINDS = {"profiles", "profile"}
FIELD_KINDS = {"fields", "field_definition"}
PART_KINDS = {"parts", "part", "geometry", "geometry_feature", "mesh", "seed", "element_control", "nodes", "elements", "element_category", "element_definition", "regions", "region", "node_sets", "node_set", "element_sets", "element_set", "surfaces", "surface", "coordinate_systems", "coordinate_system", "reference_points", "reference_point", "datums", "datum_point", "datum_vector", "datum_plane", "orientations", "orientation", "section_assignments", "section_assignment"}
ASSEMBLY_KINDS = {"assembly", "asm_regions", "asm_region", "instances", "instance", "asm_node_sets", "asm_node_set", "asm_element_sets", "asm_element_set", "asm_surfaces", "asm_surface", "asm_coordinate_systems", "asm_coordinate_system", "asm_reference_points", "asm_reference_point"}
CONSTRAINT_KINDS = {"constraints", "constraint"}
BC_KINDS = {"boundary_conditions", "supports", "support", "loads", "load"}
ANALYSIS_KINDS = {"steps", "analysis_step"}
OPTIMIZATION_KINDS = {
    "optimizations", "topology_optimization", "optimization_responses", "optimization_response",
    "optimization_objectives", "optimization_objective", "optimization_constraints", "optimization_constraint",
    "topology_filters", "topology_filter_settings", "topology_symmetries", "topology_symmetry",
    "topology_controls", "optimization_runs", "optimization_run", "optimization_iteration",
}


def stage_for_kind(kind):
    if kind in MATERIAL_KINDS: return "MATERIALS"
    if kind in SECTION_KINDS: return "SECTIONS"
    if kind in PROFILE_KINDS: return "PROFILES"
    if kind in FIELD_KINDS: return "FIELDS"
    if kind in PART_KINDS: return "PART"
    if kind in ASSEMBLY_KINDS: return "ASSEMBLY"
    if kind in CONSTRAINT_KINDS: return "CONSTRAINTS"
    if kind in BC_KINDS: return "BOUNDARY CONDITIONS"
    if kind in ANALYSIS_KINDS: return "ANALYSIS"
    if kind in OPTIMIZATION_KINDS: return "OPTIMIZATION"
    return None
