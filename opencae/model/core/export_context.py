from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExportContext:
    project: Any
    analysis: Any | None = None
    options: dict[str, Any] = field(default_factory=dict)
