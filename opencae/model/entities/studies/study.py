"""Defines the common persistent base for executable engineering studies."""

from dataclasses import dataclass

from ...core import Entity


@dataclass
class Study(Entity):
    """Base entity for analyses built around an iterative or parametric workflow."""

    study_type: str = "Study"
