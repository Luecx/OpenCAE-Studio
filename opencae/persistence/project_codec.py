from __future__ import annotations

from typing import Any

import opencae.model.entities  # registers all polymorphic model types
from opencae.model.core import decode_model, encode_model
from opencae.model.project import Project

from .legacy.project import legacy_project


def project_to_dict(project: Project) -> dict[str, Any]:
    return encode_model(project)


def project_from_dict(data: dict[str, Any]) -> Project:
    if not data.get("__type__"):
        return legacy_project(data)
    project = decode_model(data)
    if not isinstance(project, Project):
        raise TypeError("The file does not contain an OpenCAE project")
    return project
