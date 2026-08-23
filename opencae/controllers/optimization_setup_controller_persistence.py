"""Persists topology Study roots and nested setup entities through ProjectStore."""

from __future__ import annotations

from opencae.model.entities.optimization import TopologyOptimization


def save_topology(controller, candidate, current) -> None:
    """Insert or replace one TopologyOptimization Study and select it."""
    project = controller.store.project
    if not candidate.analysis_ref.entity_id:
        raise ValueError("Select an Analysis")

    current_id = getattr(current, "id", "")
    if not current_id:
        controller.store.add_entity(
            f"Created Study {candidate.name}",
            project.id,
            "studies",
            candidate,
        )
    else:
        candidate.id = current_id
        controller.store.replace_entity(
            f"Edited Study {candidate.name}",
            project.id,
            "studies",
            candidate,
        )

    controller.active_study_id = candidate.id
    controller.store.select(controller.store.project.try_resolve(candidate.id))


def save_nested(
    controller,
    study_id,
    attribute: str,
    candidate,
    current_id: str = "",
) -> None:
    """Insert or replace one nested topology configuration entity."""
    study = controller.store.project.try_resolve(study_id)
    if not isinstance(study, TopologyOptimization):
        raise ValueError("The Topology Optimization Study no longer exists")

    if not current_id:
        controller.store.add_entity(
            f"Created {candidate.name}",
            study.id,
            attribute,
            candidate,
        )
    else:
        candidate.id = current_id
        controller.store.replace_entity(
            f"Edited {candidate.name}",
            study.id,
            attribute,
            candidate,
        )

    resolved = controller.store.project.try_resolve(candidate.id)
    if resolved is None:
        # Failing here is preferable to leaving the UI selected on a stale
        # pre-command object after an undoable store replacement.
        raise ValueError("The saved Study entity could not be resolved")
    controller.store.select(resolved)
