from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).parents[1] / "opencae"


def test_domain_model_does_not_import_solvers():
    offenders = []
    for path in (ROOT / "model").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "opencae.solvers" in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_removed_duplicate_legacy_modules_stay_removed():
    for relative in ("app.py", "ui/ribbon.py", "ui/viewport.py", "core/model.py", "ui/panels.py"):
        assert not (ROOT / relative).exists()


def test_productive_consumers_do_not_import_legacy_target_types():
    modules = [
        ROOT / "model/entities/loads",
        ROOT / "model/entities/supports",
        ROOT / "model/entities/constraints",
        ROOT / "model/entities/regions/section_assignment.py",
        ROOT / "controllers/load_controller.py",
        ROOT / "controllers/part/regions.py",
    ]
    forbidden = ("TargetRef", "EntityTarget", "MeshNodeTarget", "MeshElementTarget")
    offenders = []
    paths = []
    for module in modules:
        paths.extend(module.rglob("*.py") if module.is_dir() else [module])
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if any(value in text for value in forbidden): offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_legacy_target_runtime_model_is_removed():
    text = (ROOT / "model/core/reference.py").read_text(encoding="utf-8")
    for name in ("EntityTarget", "MeshNodeTarget", "MeshElementTarget", "TargetKind", "TargetRef"):
        assert name not in text


def test_regions_expose_only_generic_definitions_not_legacy_members():
    text = (ROOT / "model/entities/regions/region.py").read_text(encoding="utf-8")
    assert "def members" not in text
    assert "RegionMemberRef" not in text


def test_productive_entities_use_strict_region_normalizer():
    offenders = []
    for path in (ROOT / "model/entities").rglob("*.py"):
        if "definition_from_target" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_direct_constructor_keywords_match_declared_signatures():
    """Catch stale keyword calls even when optional GUI packages are unavailable."""
    classes = {}
    trees = {}
    for path in ROOT.rglob("*.py"):
        try: tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError: continue
        trees[path] = tree
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                init = next((item for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__"), None)
                if init:
                    positional = [arg.arg for arg in (*init.args.posonlyargs, *init.args.args) if arg.arg != "self"]
                    keywords = [arg.arg for arg in init.args.kwonlyargs]
                    classes[node.name] = (set(positional + keywords), init.args.kwarg is not None, path)
    offenders = []
    for path, tree in trees.items():
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name): continue
            signature = classes.get(node.func.id)
            if not signature: continue
            accepted, variadic, declared = signature
            if variadic: continue
            invalid = sorted(keyword.arg for keyword in node.keywords if keyword.arg and keyword.arg not in accepted)
            if invalid: offenders.append((str(path.relative_to(ROOT)), node.lineno, node.func.id, invalid, str(declared.relative_to(ROOT))))
    assert offenders == []


def test_controllers_use_explicit_commands_not_project_snapshots():
    offenders = []
    for path in (ROOT / "controllers").rglob("*.py"):
        if ".mutate(" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []
    store = (ROOT / "store/project_store.py").read_text(encoding="utf-8")
    commands = (ROOT / "store/commands.py").read_text(encoding="utf-8")
    assert "def mutate(" not in store
    assert "PatchProjectCommand" not in commands


def test_typed_viewport_selection_replaces_free_form_pick_dictionaries():
    paths = [
        ROOT / "ui/viewport/point_selection_state.py",
        ROOT / "ui/viewport/element_selection_state.py",
        ROOT / "ui/viewport/cell_selection.py",
        ROOT / "ui/viewport/pyvista_picker.py",
        ROOT / "ui/viewport/reference_point_overlay.py",
        ROOT / "ui/viewport/datum_overlay.py",
        ROOT / "controllers/region_selection.py",
    ]
    offenders = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if '"mesh_entity"' in text or "{'kind':" in text or '{"kind":' in text or '"kind": "rp"' in text or '"kind": "datum_' in text:
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_constraint_requirements_have_one_authoritative_definition():
    controller = (ROOT / "controllers/assembly_controller_constraints.py").read_text(encoding="utf-8")
    dialog = (ROOT / "ui/dialogs/constraint.py").read_text(encoding="utf-8")
    assert "constraint_selection_policy" in controller
    assert "constraint_region_requirement" in dialog
    assert "RegionRequirement(RegionProjection.SINGLE_CONTROL_NODE" not in controller


def test_reference_selector_uses_explicit_callback_protocol():
    text = (ROOT / "ui/core/widgets/reference_selector.py").read_text(encoding="utf-8")
    assert "inspect.signature" not in text
    assert "callback(self.window(), self._apply_created)" in text


def test_femaster_load_emitter_dispatches_by_concrete_class():
    text = (ROOT / "solvers/femaster_dsl/emitters/loads.py").read_text(encoding="utf-8")
    assert 'load.load_type ==' not in text
    assert 'load.load_type in' not in text


def test_geometry_history_uses_generic_regions_not_region_members():
    feature = (ROOT / "model/entities/geometry/feature.py").read_text(encoding="utf-8")
    dialog = (ROOT / "ui/dialogs/partition.py").read_text(encoding="utf-8")
    controller = (ROOT / "controllers/part/partitions.py").read_text(encoding="utf-8")
    assert "RegionDefinition" in feature and "references:" not in feature
    assert "CompactRegionSelector" in dialog and "SelectionMembersWidget" not in dialog
    assert "begin_region_pick" in controller and "selected_labels" not in controller
    assert not (ROOT / "model/core/region_member.py").exists()
    assert not (ROOT / "ui/core/widgets/selection_members.py").exists()


def test_whole_project_json_patch_implementation_is_removed():
    assert not (ROOT / "store/json_patch.py").exists()


def test_viewport_factory_does_not_hide_runtime_construction_bugs():
    text = (ROOT / "ui/viewport/viewport_factory.py").read_text(encoding="utf-8")
    assert "except Exception" not in text
    assert "except (ImportError, ModuleNotFoundError)" in text


def test_viewport_overlays_do_not_silently_swallow_exceptions():
    offenders = []
    for path in (ROOT / "ui/viewport").glob("*.py"):
        if path.name == "safe_operations.py": continue
        text = path.read_text(encoding="utf-8")
        if "except Exception: pass" in text or "except Exception:\n            pass" in text:
            offenders.append(path.name)
    assert offenders == []


def test_partition_dialog_resolves_current_part_by_id():
    text = (ROOT / "ui/dialogs/partition.py").read_text(encoding="utf-8")
    assert "self.part_id = part.id" in text
    assert "self.project.try_resolve(self.part_id)" in text
    assert "self.part = part" not in text


def test_known_geometry_features_use_explicit_fields_not_parameter_switches():
    paths = [
        ROOT / "geometry/occ_import.py",
        ROOT / "geometry/partition_plane.py",
        ROOT / "geometry/partition_face.py",
        ROOT / "geometry/partition_edge.py",
        ROOT / "geometry/history.py",
    ]
    offenders = [str(path.relative_to(ROOT)) for path in paths if "parameters.get" in path.read_text(encoding="utf-8")]
    assert offenders == []


def test_viewport_scene_uses_instance_ids_without_name_fallbacks():
    reference = (ROOT / "ui/viewport/assembly_context.py").read_text(encoding="utf-8")
    scene = (ROOT / "ui/viewport/pyvista_scene.py").read_text(encoding="utf-8")
    assert "instance_name" not in reference
    assert "item.name == instance_key" not in scene
    assert "assembly_snapshots.get(instance_key)" in scene
    assert "assembly_instances.get(instance_key)" in scene


def test_part_and_assembly_persist_only_one_region_collection():
    for relative in ("model/entities/parts/part.py", "model/entities/assembly/assembly.py"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "regions:" in text
        assert "def node_sets" not in text
        assert "def element_sets" not in text
        assert "def surfaces" not in text


def test_runtime_region_has_no_redundant_region_type_string():
    text = (ROOT / "model/entities/regions/region.py").read_text(encoding="utf-8")
    assert "def region_type" not in text


def test_runtime_surface_resolution_does_not_guess_facets_from_node_subsets():
    text = (ROOT / "model/selection/resolution.py").read_text(encoding="utf-8")
    geometry_helper = text[text.index("def _geometry_facets"):text.index("def _boundary_facets")]
    assert "issubset" not in geometry_helper
    assert "entity_facets" in geometry_helper


def test_runtime_picker_does_not_accept_legacy_selection_dictionaries():
    hit = (ROOT / "model/selection/hit.py").read_text(encoding="utf-8")
    context = (ROOT / "ui/viewport/context_pick.py").read_text(encoding="utf-8")
    controller = (ROOT / "controllers/region_selection.py").read_text(encoding="utf-8")
    assert "from_legacy" not in hit
    assert "isinstance(value, dict)" not in context
    assert "ViewportHit.from_legacy" not in controller


def test_point_picker_filters_hidden_and_policy_incompatible_candidates():
    text = (ROOT / "ui/viewport/point_selection_state.py").read_text(encoding="utf-8")
    assert 'self.owner.display_mode != "mesh"' in text
    assert "context.accepts(SelectableKind.MESH_NODE)" in text
    assert "context.accepts(hit.kind)" in text
    assert "_actor_enabled(actor)" in text


def test_runtime_region_api_exposes_only_unified_region_type():
    package = (ROOT / "model/entities/regions/__init__.py").read_text(encoding="utf-8")
    assert '"NodeSet"' not in package
    assert '"ElementSet"' not in package
    assert '"Surface"' not in package


def test_section_assignment_has_no_legacy_single_region_property():
    text = (ROOT / "model/entities/regions/section_assignment.py").read_text(encoding="utf-8")
    assert "def region_ref" not in text


def test_known_best_effort_paths_log_instead_of_silent_pass():
    paths = [
        ROOT / "ui/tree/solution_tree.py",
        ROOT / "geometry/gmsh_session.py",
        ROOT / "geometry/mesh_controls.py",
        ROOT / "geometry/entity_names.py",
        ROOT / "geometry/entity_membership.py",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "except Exception: pass" not in text
        assert "except Exception:\n                pass" not in text


def test_cell_remove_event_is_forwarded_to_region_selection():
    text = (ROOT / "ui/viewport/cell_selection.py").read_text(encoding="utf-8")
    assert "changed = [_cell_hit" in text
    assert "hit.with_operation(operation) for hit in changed" in text


def test_partition_edit_uses_one_id_lookup_without_stale_object_indexing():
    text = (ROOT / "controllers/part/partitions.py").read_text(encoding="utf-8")
    assert "existing_index = next" in text
    assert "candidate.geometry[existing_index] = replacement" in text
    assert "candidate.geometry.index" not in text


def test_region_consumers_use_compact_selector_and_keep_detailed_editor_extended():
    consumers = [
        ROOT / "ui/dialogs/constraint.py",
        ROOT / "ui/dialogs/section_assignment.py",
        ROOT / "ui/dialogs/load_common.py",
        ROOT / "ui/dialogs/support.py",
        ROOT / "ui/dialogs/edge_seed.py",
        ROOT / "ui/dialogs/mesh_control.py",
        ROOT / "ui/dialogs/element_control_target.py",
        ROOT / "ui/dialogs/partition.py",
    ]
    for path in consumers:
        text = path.read_text(encoding="utf-8")
        assert "CompactRegionSelector" in text
        assert "RegionSelectionWidget" not in text
    compact = (ROOT / "ui/core/widgets/compact_region_selector.py").read_text(encoding="utf-8")
    extended = (ROOT / "ui/core/widgets/extended_region_dialog.py").read_text(encoding="utf-8")
    detailed = (ROOT / "ui/core/widgets/region_selection.py").read_text(encoding="utf-8")
    assert "ExtendedRegionDialog" in compact
    assert "pick_callback=None" in extended
    assert "QTableWidget" not in compact
    assert "QTableWidget" in detailed


def test_compact_region_selector_owns_one_checkable_pick_button_and_deferred_value():
    text = (ROOT / "ui/core/widgets/compact_region_selector.py").read_text(encoding="utf-8")
    assert 'self.pick_button.setCheckable(True)' in text
    assert '"Finish selecting this region"' in text
    assert "self.picking_changed.emit(bool(active))" in text
    assert "self.apply_pick," in text
    assert "self._session_finished," in text
    assert "RegionResolver" not in text
    assert "selection_item_label" in text


def test_constraint_control_point_is_direct_single_pick_without_extended_menu():
    requirements = (ROOT / "model/entities/constraints/requirements.py").read_text(encoding="utf-8")
    dialog = (ROOT / "ui/dialogs/constraint.py").read_text(encoding="utf-8")
    assert "_POINT_KINDS" in requirements
    assert "not master or kind == ConstraintType.TIE" in requirements
    assert "kind == ConstraintType.CONNECTOR" in requirements
    assert "direct_control_point_error" in dialog
    assert "self.master.set_extended_visible(tie)" in dialog


def test_load_support_and_section_dialogs_keep_persistent_preview_channels():
    loads = (ROOT / "controllers/load_controller.py").read_text(encoding="utf-8")
    constraints = (ROOT / "controllers/assembly_controller_constraints.py").read_text(encoding="utf-8")
    sections = (ROOT / "controllers/part/regions.py").read_text(encoding="utf-8")
    assert "load-support-dialog-" in loads
    assert "constraint-dialog-" in constraints
    assert "section-assignment-dialog-" in sections
    assert "clear_region_preview" in loads
    assert "clear_region_previews" in constraints
    assert "clear_region_preview" in sections
