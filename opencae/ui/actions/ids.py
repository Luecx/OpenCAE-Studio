"""Stable identifiers for centrally registered UI actions."""


class A:
    NEW_PROJECT = "project.new"; OPEN_PROJECT = "project.open"
    OPEN_RESULTS = "results.open_file"; SAVE_PROJECT = "project.save"
    SAVE_AS = "project.save_as"; PROJECT_SETTINGS = "project.settings"
    PREFERENCES = "app.preferences"; QUIT = "app.quit"
    UNDO = "edit.undo"; REDO = "edit.redo"
    EDIT_SELECTED = "edit.selected"; DELETE_SELECTED = "delete.selected"
    FIT_VIEW = "view.fit"; TOGGLE_MESH = "view.toggle_mesh"
    SHOW_PROJECT = "view.show_project"
    SHOW_JOBS = "view.show_jobs"; SHOW_LOG = "view.show_log"
    SHOW_TIME_MANAGER = "view.show_time_manager"
    # Compatibility alias for plugins/saved commands using the old Output action.
    SHOW_OUTPUT = SHOW_JOBS
    RESET_LAYOUT = "window.reset_layout"
    MATERIAL = "resource.material"; MATERIAL_BROWSER = "resource.material_browser"
    SET_ELASTICITY = "material.elasticity"
    SET_DENSITY = "material.density"; SET_PLASTICITY = "material.plasticity"
    SET_THERMAL = "material.thermal"; FIELD = "resource.field"
    SECTION_SOLID = "section.solid"; SECTION_SHELL = "section.shell"
    SECTION_BEAM = "section.beam"; SECTION_TRUSS = "section.truss"
    PROFILE_RECTANGLE = "profile.rectangle"; PROFILE_BOX = "profile.box"
    PROFILE_PIPE = "profile.pipe"; PROFILE_I = "profile.i"
    PROFILE_CHANNEL = "profile.channel"; PROFILE_U = "profile.u"
    PROFILE_H = "profile.h"; PROFILE_CIRCLE = "profile.circle"
    PROFILE_GENERAL = "profile.general"; PROFILE_GRAPH = "profile.graph"
    NEW_PART = "part.new"; DUPLICATE_PART = "part.duplicate"; IMPORT_GEOMETRY = "part.import"
    IMPORT_MESH = "part.import_mesh"; PARTITION = "part.partition"
    SUPPRESS_FEATURE = "part.suppress_feature"; REBUILD_GEOMETRY = "part.rebuild_geometry"
    DEFAULT_SEED = "mesh.default_seed"; EDGE_SEED = "mesh.edge_seed"
    ELEMENT_CONTROLS = "mesh.element_controls"; MESH_SETTINGS = "mesh.settings"
    GENERATE_MESH = "mesh.generate"; CLEAR_MESH = "mesh.clear"
    VISIBILITY = "part.visibility"
    NODE_SET = "part.node_set"
    ELEMENT_SET = "part.element_set"; SURFACE = "part.surface"
    PART_CSYS = "part.csys"; PART_RP = "part.rp"
    DATUM_POINT = "part.datum_point"; DATUM_VECTOR = "part.datum_vector"
    DATUM_PLANE = "part.datum_plane"; SECTION_ASSIGNMENT = "part.section_assignment"
    ADD_INSTANCE = "assembly.add_instance"; DUPLICATE_INSTANCE = "assembly.duplicate_instance"
    TRANSFORM_INSTANCE = "assembly.transform"; SUPPRESS_INSTANCE = "assembly.suppress"
    ASM_NODE_SET = "assembly.node_set"; ASM_ELEMENT_SET = "assembly.element_set"
    ASM_SURFACE = "assembly.surface"; ASM_CSYS = "assembly.csys"
    ASM_RP = "assembly.rp"; CONSTRAINT = "assembly.constraint"
    CONSTRAINT_KINEMATIC = "constraint.kinematic"; CONSTRAINT_DISTRIBUTING = "constraint.distributing"
    CONSTRAINT_TIE = "constraint.tie"; CONSTRAINT_RIGID = "constraint.rigid"
    CONSTRAINT_CONNECTOR = "constraint.connector"
    CONSTRAINT_EQUATION = "constraint.equation"; CONSTRAINT_MPC = "constraint.mpc"
    FIXED = "bc.fixed"; DISPLACEMENT = "bc.displacement"
    SYMMETRY = "bc.symmetry"; AMPLITUDE = "load.amplitude"
    CLOAD = "load.concentrated"; DLOAD = "load.distributed"
    PRESSURE = "load.pressure"; VLOAD = "load.volume"
    INERTIA_LOAD = "load.inertia"; TEMPERATURE = "load.temperature"

    STEP_LINEAR = "step.linear"; STEP_NONLINEAR = "step.nonlinear"
    STEP_MODAL = "step.modal"; STEP_BUCKLING = "step.buckling"
    STEP_TRANSIENT = "step.transient"; REORDER_STEPS = "step.reorder"
    STEP_MATRIX = "step.matrix"

    ANALYSIS_NEW = "analysis.new"
    ANALYSIS_EDIT = "analysis.edit"
    ANALYSIS_RUN = "analysis.run"
    DECK_FORMAT_MANAGER = "solver.deck_format_manager"
    VALIDATE = "analysis.validate"
    PREVIEW_DECK = "analysis.preview_deck"
    WRITE_DECK = "analysis.write_deck"

    # Compatibility alias: Solver Settings was folded into the one global
    # application Settings surface. It must not be registered or shown twice.
    SOLVER_SETTINGS = PREFERENCES

    STUDY_NEW_TOPOLOGY = "study.new_topology"
    STUDY_EDIT = "study.edit"
    STUDY_RUN = "study.run"
    STUDY_VALIDATE = "study.validate"
    OPT_RESPONSE = "study.topology.response"
    OPT_OBJECTIVE = "study.topology.objective"
    OPT_CONSTRAINT = "study.topology.constraint"
    OPT_FILTER = "study.topology.filter"
    OPT_SYMMETRY = "study.topology.symmetry"
    OPT_CONTROLS = "study.topology.controls"
    OPT_PREVIOUS = "study.topology.previous_iteration"
    OPT_NEXT = "study.topology.next_iteration"
    OPT_THRESHOLD = "study.topology.threshold"

    JOB_STOP = "job.stop"
    JOB_MONITOR = "job.monitor"
    JOB_OPEN_RESULTS = "job.open_results"

    # Compatibility aliases for plugins or saved UI state using the old IDs.
    OPT_NEW = STUDY_NEW_TOPOLOGY
    OPT_VALIDATE = STUDY_VALIDATE
    OPT_RUN = STUDY_RUN
    OPT_STOP = JOB_STOP
    RUN = ANALYSIS_RUN
    RESULTS = JOB_OPEN_RESULTS

    RESULT_MESH_LINES = "results.mesh_lines"
    RESULT_BOUNDARY_LINES = "results.boundary_lines"
    RESULT_DEFORM = "results.deform"
    DOCUMENTATION = "help.documentation"
    SHORTCUTS = "help.shortcuts"; ABOUT = "help.about"