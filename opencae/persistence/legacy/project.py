from pathlib import Path
from typing import Any

from opencae.model.analysis import create_analysis
from opencae.model.entities.jobs import Job, ResultSet
from opencae.model.project import Project
from opencae.model.resources import Material
from opencae.model.entities.fields import FieldDefinition

from .assembly import legacy_assembly
from .part import legacy_part
from .resources import legacy_load, legacy_profile, legacy_section, legacy_support


def legacy_project(data: dict[str, Any]) -> Project:
    return Project(
        name=data.get("name", "Untitled"),
        unit_system=data.get("unit_system", "mm-N-s-°C"),
        path=Path(data["path"]) if data.get("path") else None,
        parts=[legacy_part(dict(item)) for item in data.get("parts", [])],
        assembly=legacy_assembly(dict(data.get("assembly", {"name": "Main Assembly"}))),
        supports=[legacy_support(item) for item in data.get("supports", [])],
        loads=[legacy_load(item) for item in data.get("loads", [])],
        materials=[Material(**item) for item in data.get("materials", [])],
        profiles=[legacy_profile(item) for item in data.get("profiles", [])],
        sections=[legacy_section(item) for item in data.get("sections", [])],
        fields=[FieldDefinition(**item) for item in data.get("fields", [])],
        analyses=[_legacy_analysis(item) for item in data.get("analyses", [])],
        jobs=[Job(**item) if isinstance(item, dict) else item for item in data.get("jobs", [])],
        results=[ResultSet(**item) if isinstance(item, dict) else item for item in data.get("results", [])],
    )


def _legacy_analysis(data):
    data = dict(data)
    return create_analysis(data.pop("analysis_type", "Linear Static"), **data)
