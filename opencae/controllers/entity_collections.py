"""Enumerates every mutable entity collection in the current project graph."""


def project_collections(project):
    """Return list-backed entity collections that support generic mutations."""
    values = [
        project.parts,
        project.assembly.instances,
        project.assembly.regions,
        project.assembly.coordinate_systems,
        project.assembly.reference_points,
        project.assembly.constraints,
        project.supports,
        project.loads,
        project.materials,
        project.sections,
        project.profiles,
        project.fields,
        project.steps,
        project.analyses,
        project.studies,
        project.jobs,
        project.results,
    ]
    for study in project.studies:
        for attribute in (
            "responses",
            "objectives",
            "constraints",
            "filters",
            "symmetries",
            "controls",
            "runs",
        ):
            collection = getattr(study, attribute, None)
            if isinstance(collection, list):
                values.append(collection)
        for run in getattr(study, "runs", ()):
            iterations = getattr(run, "iterations", None)
            if isinstance(iterations, list):
                values.append(iterations)
    for part in project.parts:
        values.extend(
            [
                part.geometry,
                part.mesh.seeds,
                part.mesh.element_controls,
                part.mesh.element_definitions,
                part.regions,
                part.coordinate_systems,
                part.reference_points,
                part.datums,
                part.orientations,
                part.section_assignments,
            ]
        )
    return [value for value in values if isinstance(value, list)]
