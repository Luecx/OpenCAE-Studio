"""Builds Study definitions and their type-specific setup branches."""

from .tree_items import ensure_expandable, folder, item


def append_studies(root, studies):
    """Append Study definitions; concrete executions live only in Jobs."""

    values = tuple(studies or ())
    branch = folder("Studies", "studies", count=len(values))
    root.appendRow(branch)
    for study in values:
        label = f"{study.name}  [{getattr(study, 'study_type', type(study).__name__)}]"
        node = item(label, study, "topology_optimization")
        branch.appendRow(node)
        _append_group(
            node,
            "Responses",
            study.responses,
            "study_responses",
            "optimization_response",
        )
        _append_group(
            node,
            "Objectives",
            study.objectives,
            "study_objectives",
            "optimization_objective",
        )
        _append_group(
            node,
            "Constraints",
            study.constraints,
            "study_constraints",
            "optimization_constraint",
        )
        _append_group(
            node,
            "Filters",
            study.filters,
            "study_filters",
            "topology_filter_settings",
        )
        _append_group(
            node,
            "Symmetry Constraints",
            study.symmetries,
            "study_symmetries",
            "topology_symmetry",
        )
        _append_group(
            node,
            "Controls",
            study.controls,
            "study_controls",
            "topology_controls",
        )
    ensure_expandable(branch, values, "No Studies")
    return branch


def append_optimizations(root, optimizations):
    """Compatibility wrapper for callers using the former name."""

    return append_studies(root, optimizations)


def _append_group(parent, title, values, folder_kind, child_kind):
    values = tuple(values or ())
    node = folder(title, folder_kind, count=len(values))
    parent.appendRow(node)
    for value in values:
        node.appendRow(item(value.name, value, child_kind))
    ensure_expandable(node, values, f"No {title.lower()}")
