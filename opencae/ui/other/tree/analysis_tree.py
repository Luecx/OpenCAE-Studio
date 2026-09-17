"""Builds the separate Steps and Analyses branches of the project tree."""

from .tree_items import ensure_expandable, folder, item


def append_steps(root, steps):
    group = folder("Steps", "steps", count=len(steps))
    root.appendRow(group)
    for step in steps:
        group.appendRow(
            item(
                f"{step.name}  [{step.step_type}]",
                step,
                "analysis_step",
            )
        )
    return ensure_expandable(group, steps, "No steps")


def append_analyses(root, analyses, project):
    group = folder("Analyses", "analyses", count=len(analyses))
    root.appendRow(group)
    for analysis in analyses:
        analysis_item = item(analysis.name, analysis, "analysis")
        group.appendRow(analysis_item)
        steps = analysis.resolved_steps(project)
        for index, step in enumerate(steps, start=1):
            analysis_item.appendRow(
                item(
                    f"{index}. {step.name}  [{step.step_type}]",
                    step,
                    "analysis_step_reference",
                )
            )
        ensure_expandable(analysis_item, steps, "No referenced steps")
    return ensure_expandable(group, analyses, "No analyses")
