"""Build type-specific Study branches without topology-only controls on mesh studies."""

from opencae.model.entities.studies import MeshConvergenceStudy

from .tree_items import ensure_expandable, folder, item


def append_studies(root, studies):
    values = tuple(studies or ())
    branch = folder("Studies", "studies", count=len(values))
    root.appendRow(branch)
    for study in values:
        node = item(study.name, study, "study")
        branch.appendRow(node)
        if isinstance(study, MeshConvergenceStudy):
            _append_convergence_controls(node, study)
            continue
        _append_group(
            node,
            "Responses",
            getattr(study, "responses", ()),
            "study_responses",
            "study_response",
        )
        _append_group(
            node,
            "Objectives",
            getattr(study, "objectives", ()),
            "study_objectives",
            "study_objective",
        )
        _append_group(
            node,
            "Constraints",
            getattr(study, "constraints", ()),
            "study_constraints",
            "study_constraint",
        )
        _append_group(
            node,
            "Filters",
            getattr(study, "filters", ()),
            "study_filters",
            "study_filter",
        )
        _append_group(
            node,
            "Symmetry Constraints",
            getattr(study, "symmetries", ()),
            "study_symmetries",
            "study_symmetry",
        )
        _append_group(
            node,
            "Controls",
            getattr(study, "controls", ()),
            "study_controls",
            "study_control",
        )
    return ensure_expandable(branch, values, "No studies")


def _append_group(parent, title, values, folder_kind, child_kind):
    values = tuple(values or ())
    node = folder(title, folder_kind, count=len(values))
    parent.appendRow(node)
    for value in values:
        node.appendRow(item(value.name, value, child_kind))
    ensure_expandable(node, values, f"No {title.lower()}")


def _append_convergence_controls(parent, study):
    controls = folder("Displacement Controls", "study_displacement_controls", count=len(study.metrics))
    parent.appendRow(controls)
    for metric in study.metrics:
        node = folder(str(metric.get("name", "Displacement Control")), "study_displacement_control")
        controls.appendRow(node)
    ensure_expandable(controls, study.metrics, "No displacement controls")
