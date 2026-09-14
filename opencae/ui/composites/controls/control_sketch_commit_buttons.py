"""Sketcher commit/cancel button box with the existing viewport-toolbar chrome."""

from PyQt6.QtWidgets import QDialogButtonBox, QWidget


class ControlSketchCommitButtons(QDialogButtonBox):
    """Keep the Sketcher commit box semantically grouped and visually unchanged."""

    def __init__(
        self,
        *,
        create_mode: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok,
            parent=parent,
        )
        self.setObjectName("SketchCommitButtons")
        ok = self.button(QDialogButtonBox.StandardButton.Ok)
        if ok is not None:
            ok.setText("Create Feature" if create_mode else "Apply")
