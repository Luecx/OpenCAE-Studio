from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
)


class ImportMeshReportDialog(QDialog):
    """Show every keyword block that an orphan-mesh import did not consume."""

    def __init__(self, report, source_name: str = "input deck", parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mesh import report")
        self.setMinimumSize(620, 360)
        layout = QVBoxLayout(self)

        issues = list(getattr(report, "not_imported", ()) or ())
        warnings = list(getattr(report, "warnings", ()) or ())
        if issues:
            summary = QLabel(
                f"{source_name} was imported as an orphan mesh, but "
                f"{len(issues)} keyword block(s) were not fully imported. "
                "Every affected block is listed below."
            )
        else:
            summary = QLabel(
                f"{source_name} was imported. No unsupported keyword blocks were found."
            )
        summary.setWordWrap(True)
        layout.addWidget(summary)

        details = QPlainTextEdit(self)
        details.setReadOnly(True)
        details.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        details.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        lines = []
        if issues:
            lines.append("NOT IMPORTED KEYWORDS")
            lines.append("=====================")
            lines.extend(issue.format() for issue in issues)
        if warnings:
            if lines:
                lines.append("")
            lines.append("IMPORT WARNINGS")
            lines.append("===============")
            lines.extend(str(warning) for warning in warnings)
        if not lines:
            lines.append("All encountered keyword blocks were imported.")
        details.setPlainText("\n".join(lines))
        layout.addWidget(details, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok, parent=self)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)


__all__ = ["ImportMeshReportDialog"]
