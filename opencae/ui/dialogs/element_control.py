"""Provides the modeless element topology/order conversion editor."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from opencae.ui.templates import SectionHeading, apply_close_buttons, dialog_layout

from .element_control_order import ElementOrderPanel
from .element_control_preview import ElementControlPreview
from .element_control_target import ElementControlTarget
from .element_control_topologies import ElementTopologyTable


class ElementControlDialog(QDialog):
    """Analyze a target region and commit one topology/order/formulation conversion."""

    committed = pyqtSignal(object)
    preview_changed = pyqtSignal(object)

    def __init__(
        self,
        project,
        analyze,
        preview,
        *,
        options=(),
        pick_region=None,
        control=None,
        initial=None,
        parent=None,
    ):
        """Build target, topology, interpolation and propagation-preview sections."""
        super().__init__(parent)
        self.analyze = analyze
        self.preview_provider = preview
        self.current_preview = None
        self.setWindowTitle("Element Controls")
        self.setModal(False)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self.setMinimumSize(760, 680)

        root = dialog_layout(self)
        definition = getattr(control, "target", None) if control else initial

        root.addWidget(SectionHeading("Target"))
        self.target = ElementControlTarget(project, definition, options, pick_region, self)
        root.addWidget(self.target)

        root.addWidget(SectionHeading("Topologies in Target"))
        self.topologies = ElementTopologyTable()
        root.addWidget(self.topologies)

        root.addWidget(SectionHeading("Interpolation and Formulation"))
        self.order = ElementOrderPanel()
        root.addWidget(self.order)

        root.addWidget(SectionHeading("Propagation Preview"))
        self.preview = ElementControlPreview()
        root.addWidget(self.preview)
        root.addStretch(1)

        buttons = apply_close_buttons()
        apply_button = buttons.button(QDialogButtonBox.StandardButton.Apply)
        if apply_button is not None:
            apply_button.clicked.connect(self._apply)
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)

        self.target.changed.connect(self.refresh)
        self.topologies.topology_changed.connect(self._topology_changed)
        self.order.changed.connect(self._update_preview)
        self.refresh()
        if control:
            self.topologies.select_key(control.topology)
            self.order.choose(control.order)
            self.order.set_formulation(control.formulation)

    def refresh(self, *_):
        """Re-analyze the current target while preserving the preferred topology key."""
        preferred = self.topologies.summary().key if self.topologies.summary() else None
        self.topologies.set_summaries(self.analyze(self.target.definition()), preferred)
        if self.topologies.summary() is None:
            self._topology_changed(None)

    def _topology_changed(self, summary):
        """Update order choices after selecting a topology summary."""
        self.order.set_summary(summary)
        self._update_preview()

    def _update_preview(self):
        """Refresh conversion propagation diagnostics for the active topology/order."""
        summary = self.topologies.summary()
        definition = self.target.definition()
        self.current_preview = self.preview_provider(definition, summary.key) if summary else None
        self.preview.set_preview(self.current_preview, self.order.order())
        self.preview_changed.emit(self.current_preview)

    def _apply(self):
        """Validate the conversion and emit it after optional propagation confirmation."""
        summary, order = self.topologies.summary(), self.order.order()
        if not summary or not order:
            QMessageBox.warning(
                self,
                "Element Controls",
                "Select a topology and a definite interpolation order.",
            )
            return
        if self.current_preview and self.current_preview.additional:
            text = (
                f"{self.current_preview.additional:,} neighboring elements outside the direct "
                "selection must also be converted. Continue?"
            )
            if QMessageBox.question(
                self,
                "Propagate element order",
                text,
            ) != QMessageBox.StandardButton.Yes:
                return
        self.committed.emit(
            {
                "target": self.target.definition(),
                "topology": summary.key,
                "order": order,
                "formulation": self.order.formulation.currentText(),
            }
        )
