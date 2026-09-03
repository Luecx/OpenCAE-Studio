"""Owns small layout and region-label helpers for ConstraintDialog."""

from __future__ import annotations

from PyQt6.QtWidgets import QVBoxLayout, QWidget

from opencae.model.entities.constraints import ConstraintType
from opencae.model.selection import RegionDefinition
from opencae.ui.templates import SectionHeading


def section_container(root: QVBoxLayout, title: str) -> QWidget:
    """Create one dynamic dialog section whose heading hides with its content."""
    host = QWidget()
    layout = QVBoxLayout(host)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(12)
    layout.addWidget(SectionHeading(title))
    root.addWidget(host)
    return host


def region_labels(kind) -> tuple[str, str]:
    """Return semantic master/control and slave/body captions for a constraint type."""
    return {
        ConstraintType.KINEMATIC: ("Control point", "Coupled region"),
        ConstraintType.DISTRIBUTING: ("Control point", "Distributed region"),
        ConstraintType.TIE: ("Master surface", "Slave surface"),
        ConstraintType.RIGID_BODY: ("Reference point", "Rigid body region"),
        ConstraintType.CONNECTOR: ("Node set 1", "Node set 2"),
    }.get(kind, ("Master", "Slave"))


def master_definition(constraint) -> RegionDefinition:
    """Return the stored master/control definition across supported constraint types."""
    if constraint is None:
        return RegionDefinition()
    return getattr(
        constraint,
        "control_point",
        getattr(
            constraint,
            "reference",
            getattr(constraint, "master", RegionDefinition()),
        ),
    )


def slave_definition(constraint) -> RegionDefinition:
    """Return the stored slave/body definition across supported constraint types."""
    if constraint is None:
        return RegionDefinition()
    return getattr(constraint, "body", getattr(constraint, "slave", RegionDefinition()))
