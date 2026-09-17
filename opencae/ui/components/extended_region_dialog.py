"""Provides the detailed modeless editor opened by CompactRegionSelector."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QVBoxLayout

from .region_selection import RegionSelectionWidget

if TYPE_CHECKING:
    from .compact_region_selector import CompactRegionSelector


class ExtendedRegionDialog(QDialog):
    """Edit one compact region definition while its viewport pick session remains active."""

    def __init__(self, selector: "CompactRegionSelector"):
        """Build the detailed operand editor around the selector's shared definition."""
        super().__init__(selector.window())
        self.selector = selector
        self.setWindowTitle(selector.extended_title)
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(720, 430)

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 12)
        root.setSpacing(9)
        self.editor = RegionSelectionWidget(
            selector.project,
            selector.definition(),
            selector.options,
            pick_callback=None,
            save_callback=selector.save_callback,
            parent=self,
            requirement=selector.requirement,
            allow_part_local=selector.allow_part_local,
            show_named_regions=True,
        )
        self.editor.value_changed.connect(selector._extended_value_changed)
        root.addWidget(self.editor, 1)

        row = QHBoxLayout()
        row.addStretch(1)
        close = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close.rejected.connect(self.close)
        row.addWidget(close)
        root.addLayout(row)

    def begin_selection(self) -> None:
        """Keep viewport selection active for the complete detailed-dialog lifetime."""
        if self.selector.pick_callback and not self.selector.pick_button.isChecked():
            self.selector.pick_button.setChecked(True)
        if self.selector.pick_callback:
            self.selector.pick_button.setEnabled(False)

    def set_picking(self, active: bool) -> None:
        """Accept selector lifecycle notifications without adding duplicate pick controls."""
        return None
