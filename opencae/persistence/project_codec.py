"""Encodes, migrates and decodes OpenCAE project files."""

from __future__ import annotations

from typing import Any

import opencae.model.entities  # register polymorphic model types
import opencae.model.selection
from opencae.model.core import decode_model, encode_model
from opencae.model.project import Project
from .migrations import migrate_project_data

PROJECT_FORMAT = "opencae-project"
CURRENT_SCHEMA_VERSION = 24
MINIMUM_SCHEMA_VERSION = 23
_ENVELOPE_FIELDS = {"format", "schema_version", "project"}


def project_to_dict(project: Project) -> dict[str, Any]:
    if not isinstance(project, Project):
        raise TypeError("project_to_dict() expects an OpenCAE Project")
    project.ensure_references(strict=True)
    return {
        "format": PROJECT_FORMAT,
        "schema_version": CURRENT_SCHEMA_VERSION,
        "project": encode_model(project),
    }


def project_from_dict(data: dict[str, Any]) -> Project:
    """Decode the current schema or migrate a supported predecessor."""
    if not isinstance(data, dict):
        raise ValueError("This is not an OpenCAE project file")
    unknown = set(data) - _ENVELOPE_FIELDS
    if unknown:
        raise ValueError(
            "Unknown project envelope field(s): " + ", ".join(sorted(unknown))
        )
    if set(data) != _ENVELOPE_FIELDS:
        missing = _ENVELOPE_FIELDS - set(data)
        raise ValueError(
            "Missing project envelope field(s): " + ", ".join(sorted(missing))
        )
    if data["format"] != PROJECT_FORMAT:
        raise ValueError("This is not an OpenCAE project file")
    try:
        version = int(data["schema_version"])
    except (TypeError, ValueError) as exc:
        raise ValueError("The project file has no valid schema version") from exc
    if (
        version > CURRENT_SCHEMA_VERSION
        or version < MINIMUM_SCHEMA_VERSION
    ):
        raise ValueError(
            f"Project schema {version} is not supported; supported schemas are "
            f"{MINIMUM_SCHEMA_VERSION} through {CURRENT_SCHEMA_VERSION}"
        )
    payload = (
        data
        if version == CURRENT_SCHEMA_VERSION
        else migrate_project_data(data, version, CURRENT_SCHEMA_VERSION)
    )
    project = decode_model(payload["project"])
    if not isinstance(project, Project):
        raise TypeError("The file does not contain an OpenCAE Project")
    project.ensure_references(strict=True)
    return project
