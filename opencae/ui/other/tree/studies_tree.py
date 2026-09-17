"""Builds Studies and their editable definition subsections in the project tree."""

from .tree_items import ensure_expandable, folder, item


def append_studies(root, studies):
    values = tuple(studies or ())
    branch = folder("Studies", "studies", count=len(values))
    root.appendRow(branch)
    for study in values:
        node = item(study.name, study, "study")
        branch.appendRow(node)
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
