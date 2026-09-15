"""Map OpenCAE beam elements back to their sections and result identifiers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from opencae.model.entities.elements import BeamElementDefinition
from opencae.model.entities.profiles import Profile
from opencae.model.entities.sections import BeamSection
from opencae.model.selection import local_element_ids
from opencae.solvers.femaster_dsl.element_types import element_type


@dataclass(frozen=True, slots=True)
class BeamOccurrence:
    """One beam occurrence with enough model data for physical visualization."""

    solver_element_id: int
    part_id: str
    instance_id: str
    source_element_id: int
    connectivity: tuple[int, ...]
    n1: tuple[float, float, float]
    section: BeamSection
    profile: Profile
    instance_name: str = ""

    @property
    def direction(self) -> tuple[float, float, float]:
        return self.n1


def beam_occurrences(project) -> tuple[BeamOccurrence, ...]:
    """Reproduce FEMaster export numbering and return renderable assembly beams."""
    result = []
    next_solver_id = 1
    for instance in project.assembly.instances:
        if instance.suppressed:
            continue
        part = project.try_resolve(instance.part_ref)
        if part is None:
            continue
        sections = _beam_sections(project, part)
        rotation = _rotation(instance)
        for block in part.mesh.element_blocks:
            if not block.connectivity:
                continue
            mapped_type = element_type(block.definition, len(block.connectivity[0]))
            if mapped_type is None:
                continue
            is_beam = isinstance(block.definition, BeamElementDefinition)
            for local_id, connectivity in zip(
                block.ids,
                block.connectivity,
                strict=True,
            ):
                section_profile = sections.get(int(local_id)) if is_beam else None
                if section_profile is not None:
                    section, profile = section_profile
                    n1 = rotation @ np.asarray(section.n1, dtype=float)
                    result.append(
                        BeamOccurrence(
                            solver_element_id=next_solver_id,
                            part_id=part.id,
                            instance_id=instance.id,
                            source_element_id=int(local_id),
                            connectivity=tuple(int(value) for value in connectivity),
                            n1=tuple(float(value) for value in n1),
                            section=section,
                            profile=profile,
                            instance_name=str(instance.name),
                        )
                    )
                next_solver_id += 1
    return tuple(result)


def part_beam_occurrences(project, part) -> tuple[BeamOccurrence, ...]:
    """Return renderable beams for the Part editor using local element IDs."""
    if part is None:
        return ()
    sections = _beam_sections(project, part)
    result = []
    for block in part.mesh.element_blocks:
        if not block.connectivity or not isinstance(block.definition, BeamElementDefinition):
            continue
        for local_id, connectivity in zip(block.ids, block.connectivity, strict=True):
            local_id = int(local_id)
            section_profile = sections.get(local_id)
            if section_profile is None:
                continue
            section, profile = section_profile
            result.append(
                BeamOccurrence(
                    solver_element_id=local_id,
                    part_id=part.id,
                    instance_id="",
                    source_element_id=local_id,
                    connectivity=tuple(int(value) for value in connectivity),
                    n1=tuple(float(value) for value in section.n1),
                    section=section,
                    profile=profile,
                )
            )
    return tuple(result)


def _beam_sections(project, part) -> dict[int, tuple[BeamSection, Profile]]:
    result = {}
    for assignment in part.section_assignments:
        section = project.try_resolve(assignment.section_ref)
        if not isinstance(section, BeamSection):
            continue
        profile = project.try_resolve(section.profile_ref)
        if not isinstance(profile, Profile):
            continue
        for element_id in local_element_ids(part, assignment.target):
            result[int(element_id)] = (section, profile)
    return result


def _rotation(instance) -> np.ndarray:
    angles = np.radians(np.asarray(instance.rotation, dtype=float))
    cx, cy, cz = np.cos(angles)
    sx, sy, sz = np.sin(angles)
    rx = np.asarray(((1, 0, 0), (0, cx, -sx), (0, sx, cx)), dtype=float)
    ry = np.asarray(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)), dtype=float)
    rz = np.asarray(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)), dtype=float)
    return rz @ ry @ rx
