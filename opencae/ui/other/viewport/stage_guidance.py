"""Defines viewport guidance for workflow stages that require an assembly."""

from __future__ import annotations

ASSEMBLY_REQUIRED_STAGES = frozenset(
    {
        "ASSEMBLY",
        "CONSTRAINTS",
        "BOUNDARY CONDITIONS",
        "STEPS",
        "ANALYSIS",
        "STUDIES",
    }
)


def assembly_guidance(stage: str, project) -> tuple[str, str] | None:
    """Return an empty-assembly notice for assembly-dependent workflow stages."""
    if str(stage) not in ASSEMBLY_REQUIRED_STAGES or project is None:
        return None
    instances = getattr(getattr(project, "assembly", None), "instances", ())
    if any(not getattr(instance, "suppressed", False) for instance in instances):
        return None
    return (
        "Assembly has no active instances",
        "Create an assembly instance before using assembly, constraint, "
        "boundary-condition, analysis, or study tools.",
    )
