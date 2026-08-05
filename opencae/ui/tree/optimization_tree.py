"""Builds Optimization, response, constraint, run and iteration tree nodes."""

from .tree_items import ensure_expandable, folder, item


def append_optimizations(root, optimizations):
    """Append all topology definitions and run histories to the project tree."""

    values = tuple(optimizations or ())
    branch = folder("Optimization", "optimizations", count=len(values))
    root.appendRow(branch)
    for optimization in values:
        node = item(
            optimization.name,
            optimization,
            "topology_optimization",
        )
        branch.appendRow(node)
        _append_group(
            node,
            "Responses",
            optimization.responses,
            "optimization_responses",
            "optimization_response",
        )
        _append_group(
            node,
            "Objectives",
            optimization.objectives,
            "optimization_objectives",
            "optimization_objective",
        )
        _append_group(
            node,
            "Constraints",
            optimization.constraints,
            "optimization_constraints",
            "optimization_constraint",
        )
        _append_group(
            node,
            "Filters",
            optimization.filters,
            "topology_filters",
            "topology_filter_settings",
        )
        _append_group(
            node,
            "Symmetry Constraints",
            optimization.symmetries,
            "topology_symmetries",
            "topology_symmetry",
        )
        _append_group(
            node,
            "Controls",
            optimization.controls,
            "topology_controls",
            "topology_controls",
        )
        runs = folder(
            "Runs",
            "optimization_runs",
            count=len(optimization.runs),
        )
        node.appendRow(runs)
        for run in optimization.runs:
            suffix = f" — {run.status}" if run.status else ""
            run_node = item(
                f"{run.name}{suffix}",
                run,
                "optimization_run",
            )
            runs.appendRow(run_node)
            for iteration in run.iterations:
                label = (
                    f"Iteration {iteration.number}  "
                    f"f={iteration.objective_value:.6g}  "
                    f"Δρ={iteration.maximum_density_change:.3g}"
                )
                run_node.appendRow(
                    item(label, iteration, "optimization_iteration")
                )
            ensure_expandable(
                run_node,
                run.iterations,
                "No iterations",
            )
        ensure_expandable(runs, optimization.runs, "No runs")
    ensure_expandable(branch, values, "No topology optimizations")
    return branch


def _append_group(parent, title, values, folder_kind, child_kind):
    values = tuple(values or ())
    node = folder(title, folder_kind, count=len(values))
    parent.appendRow(node)
    for value in values:
        node.appendRow(item(value.name, value, child_kind))
    ensure_expandable(node, values, f"No {title.lower()}")
