from pathlib import Path
from typing import Any

from opencae.model.analysis import AnalysisStep, create_analysis
from opencae.model.core import EntityRef
from opencae.model.entities.jobs import Job, ResultSet
from opencae.model.project import Project
from opencae.model.resources import Material
from opencae.model.entities.fields import FieldDefinition

from .assembly import legacy_assembly
from .part import legacy_part
from .resources import legacy_load, legacy_profile, legacy_section, legacy_support


def legacy_project(data: dict[str, Any]) -> Project:
    project = Project(
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
        fields=[_legacy_field(item) for item in data.get("fields", [])],
        analyses=[_legacy_analysis(item) for item in data.get("analyses", [])],
        jobs=[_legacy_job(item) if isinstance(item, dict) else item for item in data.get("jobs", [])],
        results=[_legacy_result(item) if isinstance(item, dict) else item for item in data.get("results", [])],
    )
    project.ensure_references(False)
    return project


def _legacy_analysis(data):
    values = dict(data)
    analysis_type = values.pop("analysis_type", "Linear Static")
    if "steps" in values:
        values["steps"] = [_legacy_step(item, analysis_type) for item in values["steps"]]
    return create_analysis(analysis_type, **values)


def _legacy_step(value, default_type):
    if isinstance(value, str):
        return AnalysisStep(name=value, step_type=default_type)
    data = dict(value)
    loads = data.pop("active_loads", ())
    supports = data.pop("active_supports", ())
    if loads and "load_refs" not in data:
        data["load_refs"] = [EntityRef(expected_type="Load", legacy_name=name) for name in loads]
    if supports and "support_refs" not in data:
        data["support_refs"] = [EntityRef(expected_type="Support", legacy_name=name) for name in supports]
    return AnalysisStep(**data)


def _legacy_field(data):
    values = dict(data)
    region = values.pop("region_name", "")
    if region and "region_ref" not in values:
        values["region_ref"] = EntityRef(expected_type="Region", legacy_name=region)
    return FieldDefinition(**values)


def _legacy_job(data):
    values = dict(data)
    analysis = values.pop("analysis_name", "")
    if analysis and analysis != "All Steps" and "analysis_ref" not in values:
        values["analysis_ref"] = EntityRef(expected_type="Analysis", legacy_name=analysis)
    return Job(**values)


def _legacy_result(data):
    values = dict(data)
    job = values.pop("job_name", "")
    if job and job != "External" and "job_ref" not in values:
        values["job_ref"] = EntityRef(expected_type="Job", legacy_name=job)
    return ResultSet(**values)
