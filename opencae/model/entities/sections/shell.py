from dataclasses import dataclass, field
from ...core import register_model_type
from .base import Section


def _matrix(rows, columns): return [[0.0 for _ in range(columns)] for _ in range(rows)]

@register_model_type("shell_section")
@dataclass
class ShellSection(Section):
    section_type: str = field(init=False, default="Shell")
    shell_definition: str = "Integrated shell section"
    thickness: float = 1.0
    integration_points: int = 5
    abd_matrix: list[list[float]] = field(default_factory=lambda: _matrix(6, 6))
    shear_matrix: list[list[float]] = field(default_factory=lambda: _matrix(2, 2))
