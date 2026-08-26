"""Encodes and decodes the single current OpenCAE project file format."""

from __future__ import annotations

from typing import Any

import opencae.model.entities  # register polymorphic model types
import opencae.model.selection
from opencae.model.core import decode_model, encode_model
from opencae.model.project import Project

PROJECT_FORMAT = "opencae-project"
CURRENT_SCHEMA_VERSION = 23
_ENVELOPE_FIELDS = {"format", "schema_version", "project"}


def project_to_dict(project: Project) -> dict[str, Any]:
    """Encode one valid Project using only the current development schema."""
    if not isinstance(project, Project):
        raise TypeError("project_to_dict() expects an OpenCAE Project")
    project.ensure_references(strict=True)
    return {
        "format": PROJECT_FORMAT,
        "schema_version": CURRENT_SCHEMA_VERSION,
        "project": encode_model(project),
    }


def project_from_dict(data: dict[str, Any]) -> Project:
    """Decode one file written by the current development schema.

    OpenCAE is still in development, so older schemas are intentionally rejected
    instead of carrying migration and compatibility layers in runtime code.
    """
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
    if version != CURRENT_SCHEMA_VERSION:
        raise ValueError(
            f"Project schema {version} is not supported by this development "
            f"build; schema {CURRENT_SCHEMA_VERSION} is required"
        )

    project = decode_model(data["project"])
    if not isinstance(project, Project):
        raise TypeError("The file does not contain an OpenCAE Project")
    project.ensure_references(strict=True)
    return project
