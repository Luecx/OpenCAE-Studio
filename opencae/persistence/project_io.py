from __future__ import annotations
import json
from pathlib import Path
from opencae.model.project import Project
from .project_codec import project_from_dict, project_to_dict


def save_project(project: Project, path: Path) -> None:
    project.path = path
    path.write_text(json.dumps(project_to_dict(project), indent=2), encoding="utf-8")


def load_project(path: Path) -> Project:
    project = project_from_dict(json.loads(path.read_text(encoding="utf-8")))
    project.path = path
    return project
