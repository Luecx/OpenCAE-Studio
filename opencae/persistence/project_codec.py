"""Encodes current project files and applies explicitly supported migrations."""

from __future__ import annotations

from typing import Any

import opencae.model.entities  # register polymorphic model types
import opencae.model.selection
from opencae.model.core import decode_model, encode_model
from opencae.model.project import Project

from .mesh_definition_migration import (
    SOURCE_SCHEMA_VERSION,
    TARGET_SCHEMA_VERSION,
    migrate_mesh_definitions,
)

CURRENT_SCHEMA_VERSION = TARGET_SCHEMA_VERSION


def project_to_dict(project: Project) -> dict[str, Any]:
    """Encode one Project using the current persistent schema."""
    project.schema_version = CURRENT_SCHEMA_VERSION
    project.ensure_references(strict=False)
    return encode_model(project)


def project_from_dict(data: dict[str, Any]) -> Project:
    """Decode a current Project, migrating the directly preceding schema."""
    if not isinstance(data, dict) or data.get("__type__") != "project":
        raise ValueError("This is not a current OpenCAE project file")
    try:
        version = int(data.get("schema_version"))
    except (TypeError, ValueError) as exc:
        raise ValueError("The project file has no valid schema version") from exc

    if version == SOURCE_SCHEMA_VERSION:
        data = migrate_mesh_definitions(data)
        version = CURRENT_SCHEMA_VERSION
    if version != CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Project schema {version} is not supported by this development "
            f"build; schema {CURRENT_SCHEMA_VERSION} is required"
        )

    project = decode_model(data)
    if not isinstance(project, Project):
        raise TypeError("The file does not contain an OpenCAE project")
    project.ensure_references(strict=False)
    return project
