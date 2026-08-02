from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Region:
    name: str
    kind: str
    count: int = 0


@dataclass(slots=True)
class Part:
    name: str
    geometry_source: str = 'Parametric'
    material: str = 'Aluminum 6061-T6'
    section: str = 'Solid Section'
    mesh_variant: str = 'Default'
    element_type: str = 'C3D10'
    global_size: float = 5.0
    nodes: int = 241_890
    elements: int = 152_624
    regions: list[Region] = field(default_factory=lambda: [
        Region('MOUNTING_HOLES', 'Node Set', 384),
        Region('LOAD_FACE', 'Surface', 928),
        Region('ALL_ELEMENTS', 'Element Set', 152_624),
    ])


@dataclass(slots=True)
class Instance:
    name: str
    part_name: str
    visible: bool = True


@dataclass(slots=True)
class BoundaryCondition:
    name: str
    kind: str
    region: str
    step: str = 'Initial'


@dataclass(slots=True)
class Load:
    name: str
    kind: str
    region: str
    magnitude: str
    step: str = 'Step-1'


@dataclass(slots=True)
class Analysis:
    name: str
    kind: str
    solver: str = 'FEMaster'
    step: str = 'Step-1'
    status: str = 'Ready'


@dataclass
class ProjectModel:
    name: str = 'Bracket Study'
    path: Path | None = None
    unit_system: str = 'mm, N, MPa'
    parts: list[Part] = field(default_factory=lambda: [Part('Bracket'), Part('Plate'), Part('Pin')])
    instances: list[Instance] = field(default_factory=lambda: [
        Instance('Bracket-1', 'Bracket'),
        Instance('Plate-1', 'Plate'),
        Instance('Pin-1', 'Pin'),
    ])
    boundary_conditions: list[BoundaryCondition] = field(default_factory=lambda: [
        BoundaryCondition('Fixed Support', 'Fixed', 'Assembly/MOUNTING_HOLES'),
    ])
    loads: list[Load] = field(default_factory=lambda: [
        Load('Pressure Load', 'Pressure', 'Assembly/LOAD_FACE', '5.0 MPa'),
        Load('Point Load', 'Force', 'Assembly/REFERENCE_POINT', '1000 N'),
    ])
    analyses: list[Analysis] = field(default_factory=lambda: [
        Analysis('Static-1', 'Linear Static'),
        Analysis('Modal-1', 'Modal'),
    ])
    metadata: dict[str, Any] = field(default_factory=dict)

    def active_part(self) -> Part:
        return self.parts[0]
