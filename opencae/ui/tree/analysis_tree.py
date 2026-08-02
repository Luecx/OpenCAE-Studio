from .tree_items import ensure_expandable, folder, item


def append_steps(root, analyses):
    group = folder("Steps", "steps"); root.appendRow(group); steps = []
    for analysis in analyses:
        for step in analysis.steps:
            steps.append(step); group.appendRow(item(f"{step.name}  [{step.step_type}]", step, "analysis_step"))
    return ensure_expandable(group, steps, "No steps")
