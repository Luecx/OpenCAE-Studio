def project_collections(project):
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
        project.analyses,
        project.jobs,
        project.results,
    ]
    for analysis in project.analyses:
        steps = getattr(analysis, "steps", None)
        if isinstance(steps, list):
            values.append(steps)
    for part in project.parts:
        values.extend([
            part.geometry,
            part.mesh.seeds,
            part.mesh.controls,
            part.mesh.element_controls,
            part.mesh.elements,
            part.regions,
            part.coordinate_systems,
            part.reference_points,
            part.datums,
            part.orientations,
            part.section_assignments,
        ])
    return [value for value in values if isinstance(value, list)]
