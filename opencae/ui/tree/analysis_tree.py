from .tree_items import ensure_expandable, folder, item


def append_steps(root, analyses):
    steps = [step for analysis in analyses for step in analysis.steps]
    group = folder("Steps", "steps", count=len(steps)); root.appendRow(group)
    for step in steps:
        group.appendRow(item(f"{step.name}  [{step.step_type}]", step, "analysis_step"))
    return ensure_expandable(group, steps, "No steps")
