"""Reads and atomically writes current OpenCAE project files."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from opencae.model.project import Project

from .project_codec import project_from_dict, project_to_dict


def save_project(project: Project, path: Path) -> None:
    """Atomically write ``project`` and update its runtime path on success only."""
    target = Path(path)
    payload = json.dumps(project_to_dict(project), indent=2)
    target.parent.mkdir(parents=True, exist_ok=True)

    descriptor, temporary_name = tempfile.mkstemp(
        dir=target.parent,
        prefix=f".{target.name}.",
        suffix=".tmp",
        text=True,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, target)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise

    project.path = target


def load_project(path: Path) -> Project:
    """Load and strictly validate one current-format Project file."""
    source = Path(path)
    project = project_from_dict(
        json.loads(source.read_text(encoding="utf-8"))
    )
    project.path = source
    return project
