"""Canonical QLabel with semantic style roles."""

from __future__ import annotations

from PyQt6.QtWidgets import QLabel, QWidget

from .label_role import LabelRole
from .label_spec import LabelSpec


class SemanticLabel(QLabel):
    """Render reusable text through semantic object-name style hooks."""

    def __init__(
        self,
        spec: LabelSpec | str,
        *,
        role: LabelRole = LabelRole.BODY,
        object_name: str = "",
        parent: QWidget | None = None,
    ) -> None:
        resolved = spec if isinstance(spec, LabelSpec) else LabelSpec(str(spec), role)
        super().__init__(resolved.text, parent)
        if object_name:
            self.setObjectName(object_name)
        elif resolved.role is LabelRole.TITLE:
            self.setObjectName("PanelTitle")
        elif resolved.role is LabelRole.MUTED:
            self.setObjectName("MutedLabel")
        elif resolved.role is LabelRole.GROUP:
            self.setObjectName("GroupLabel")
        if resolved.tooltip:
            self.setToolTip(resolved.tooltip)
