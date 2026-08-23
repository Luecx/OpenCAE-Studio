"""Normalizes legacy in-memory Project graph shapes after construction.

These helpers preserve compatibility for direct ``Project(...)`` construction and
``decode_model`` round-trips while keeping migration algorithms out of the
Project aggregate class itself.
"""

from __future__ import annotations


def migrate_project_graph(project) -> None:
    """Apply all graph-shape compatibility migrations to ``project`` in order."""
    migrate_material_fields(project)
    migrate_shared_steps(project)
    migrate_studies(project)


def migrate_material_fields(project) -> None:
    """Move legacy Material-owned field definitions to the Project collection."""
    known = {item.name for item in project.fields}
    for material in project.materials:
        for item in getattr(material, "fields", ()):
            if item.name not in known:
                project.fields.append(item)
                known.add(item.name)
        if hasattr(material, "fields"):
            # The project collection is the sole canonical owner after migration.
            material.fields.clear()


def migrate_shared_steps(project) -> None:
    """Move legacy Analysis-owned Steps to the shared Project collection."""
    by_id = {step.id: step for step in project.steps}
    for analysis in project.analyses:
        if not analysis.step_refs:
            ordered = []
            for step in tuple(analysis.steps):
                stored = by_id.get(step.id)
                if stored is None:
                    project.steps.append(step)
                    by_id[step.id] = step
                    stored = step
                ordered.append(stored)
            if ordered:
                analysis.bind_steps(ordered)

        # Once references exist, keeping a second owned Step collection would
        # create two possible identities for the same conceptual Step.
        analysis.steps = []


def migrate_studies(project) -> None:
    """Merge the former optimizations collection into canonical Studies."""
    known = {item.id for item in project.studies}
    for study in tuple(project.optimizations):
        if study.id not in known:
            project.studies.append(study)
            known.add(study.id)

    # Keep the non-serialized compatibility attribute as a live alias because
    # older Python integrations may still inspect it during the migration era.
    project.optimizations = project.studies
