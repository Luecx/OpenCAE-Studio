"""Registers every centrally defined action exactly once."""

from . import (
    analysis_actions,
    assembly_actions,
    job_actions,
    load_actions,
    optimization_actions,
    part_actions,
    project_actions,
    resource_actions,
    view_actions,
)


def register_actions(registry, controllers, window, store):
    groups = (
        project_actions.specs(controllers, window, store),
        resource_actions.specs(controllers),
        part_actions.specs(controllers),
        assembly_actions.specs(controllers),
        load_actions.specs(controllers),
        analysis_actions.specs(controllers),
        optimization_actions.specs(controllers),
        job_actions.specs(controllers),
        view_actions.specs(window),
    )
    for specs in groups:
        for spec in specs:
            registry.add(spec)
