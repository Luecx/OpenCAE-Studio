from __future__ import annotations

from typing import Any

import opencae.model.entities  # registers all polymorphic model types
import opencae.model.selection  # registers region/selection model types
from opencae.model.core import decode_model, encode_model
from opencae.model.project import Project

from .legacy.project import legacy_project
from .migrations import CURRENT_SCHEMA_VERSION, migrate_project_data


def project_to_dict(project: Project) -> dict[str, Any]:
    project.schema_version = CURRENT_SCHEMA_VERSION
    project.ensure_references(strict=False)
    return encode_model(project)


def project_from_dict(data: dict[str, Any]) -> Project:
    if not data.get("__type__"):
        return legacy_project(data)
    migrated, report = migrate_project_data(data)
    project = decode_model(migrated)
    if not isinstance(project, Project):
        raise TypeError("The file does not contain an OpenCAE project")
    from opencae.model.core.reference_binding import repair_project_references
    repair_errors = repair_project_references(project)
    project.ensure_references(strict=False)
    project.reference_errors[:0] = repair_errors
    project.metadata["migration"] = {
        "source_version": report.source_version,
        "target_version": report.target_version,
        "changes": list(report.changes),
    } if report.migrated else project.metadata.get("migration", {})
    return project
