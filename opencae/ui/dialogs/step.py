"""Provides the analysis-step editor using shared fields and checked entity lists."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDoubleSpinBox,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.ui.core.widgets import ChevronComboBox
from opencae.ui.templates import (
    CheckList,
    SectionHeading,
    apply_primary_control_height,
    dialog_buttons,
    field_block,
    field_row,
)


class StepDialog(QDialog):
    """Edit one analysis step and the loads/supports active during that step."""

    def __init__(self, step, loads, supports, parent=None, existing_names=()):
        """Build type-dependent step settings plus reusable checked entity selectors."""
        super().__init__(parent)
        self.step = step
        self.existing_names = tuple(existing_names)
        self.setWindowTitle(f"Edit {step.name}")
        self.setMinimumSize(720, 680 if step.step_type == "Nonlinear Static" else 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(16)

        self.name = QLineEdit(step.name)
        apply_primary_control_height(self.name)
        self.modes = QSpinBox()
        self.modes.setRange(1, 100000)
        self.modes.setValue(step.number_of_modes)
        apply_primary_control_height(self.modes)

        if step.step_type in {"Eigenfrequency", "Linear Buckling"}:
            root.addWidget(
                field_row(
                    field_block("Name", self.name),
                    field_block("Number of modes", self.modes),
                )
            )
        else:
            root.addWidget(field_block("Name", self.name))

        self._nonlinear_settings = None
        if step.step_type == "Nonlinear Static":
            root.addWidget(SectionHeading("Nonlinear Controls"))
            root.addWidget(self._build_nonlinear_controls())

        root.addWidget(SectionHeading("Active Entities"))
        support_ids = [ref.entity_id for ref in step.support_refs]
        self.supports = CheckList(supports, support_ids)
        support_field = field_block("Active supports", self.supports)

        self.loads = None
        if step.uses_loads:
            load_ids = [ref.entity_id for ref in step.load_refs]
            self.loads = CheckList(loads, load_ids)
            root.addWidget(
                field_row(
                    support_field,
                    field_block("Active loads", self.loads),
                )
            )
        else:
            root.addWidget(support_field)
        root.addStretch(1)

        buttons = dialog_buttons()
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_nonlinear_controls(self):
        settings = dict(self.step.settings or {})
        control = str(settings.get("control", "LOAD")).upper()
        if control == "ARC_LENGTH":
            control = "PATH"

        tabs = QTabWidget()
        tabs.setObjectName("NonlinearStepTabs")

        increments = QWidget()
        increment_layout = QVBoxLayout(increments)
        increment_layout.setContentsMargins(10, 10, 10, 10)
        increment_layout.setSpacing(10)

        self.nonlinear_control = ChevronComboBox()
        self.nonlinear_control.addItem("Load control", "LOAD")
        self.nonlinear_control.addItem("Path control", "PATH")
        index = self.nonlinear_control.findData(control)
        self.nonlinear_control.setCurrentIndex(max(index, 0))

        self.max_increments = self._integer(
            settings.get("max_increments", 100), 1, 1_000_000
        )
        self.max_iterations = self._integer(
            settings.get("max_iterations", 25), 1, 10_000
        )
        increment_layout.addWidget(
            field_row(
                field_block("Control method", self.nonlinear_control),
                field_block("Maximum increments", self.max_increments),
                field_block("Iterations / increment", self.max_iterations),
            )
        )

        self.control_stack = QStackedWidget()
        self.control_stack.addWidget(self._build_load_control_page(settings))
        self.control_stack.addWidget(self._build_path_control_page(settings))
        increment_layout.addWidget(self.control_stack)

        self.adaptive = QCheckBox("Automatic / adaptive increment sizing")
        self.adaptive.setChecked(bool(settings.get("adaptive", True)))
        increment_layout.addWidget(self.adaptive)
        tabs.addTab(increments, "Incrementation")

        convergence = QWidget()
        convergence_layout = QVBoxLayout(convergence)
        convergence_layout.setContentsMargins(10, 10, 10, 10)
        convergence_layout.setSpacing(10)

        self.tolerance = self._number(settings.get("tolerance", 1.0e-8), 1e-15, 1.0)
        self.growth_factor = self._number(settings.get("growth_factor", 1.5), 1.0, 100.0)
        self.cutback_factor = self._number(settings.get("cutback_factor", 0.5), 1e-6, 1.0)
        convergence_layout.addWidget(
            field_row(
                field_block("Convergence tolerance", self.tolerance),
                field_block("Growth factor", self.growth_factor),
                field_block("Cutback factor", self.cutback_factor),
            )
        )

        self.fast_iterations = self._integer(
            settings.get("fast_iterations", 6), 1, 10_000
        )
        self.slow_iterations = self._integer(
            settings.get("slow_iterations", 10), 1, 10_000
        )
        self.maximum_cutbacks = self._integer(
            settings.get("maximum_cutbacks", 20), 0, 10_000
        )
        convergence_layout.addWidget(
            field_row(
                field_block("Fast convergence", self.fast_iterations),
                field_block("Slow convergence", self.slow_iterations),
                field_block("Maximum cutbacks", self.maximum_cutbacks),
            )
        )

        self.regularize_zero_rows = QCheckBox("Regularize weak / zero tangent rows")
        self.regularize_zero_rows.setChecked(
            bool(settings.get("regularize_zero_rows", False))
        )
        self.regularization_alpha = self._number(
            settings.get("regularization_alpha", 1.0e-4), 0.0, 1.0e12
        )
        convergence_layout.addWidget(self.regularize_zero_rows)
        convergence_layout.addWidget(
            field_block("Regularization scale", self.regularization_alpha)
        )
        convergence_layout.addStretch(1)
        tabs.addTab(convergence, "Convergence")

        self.nonlinear_control.currentIndexChanged.connect(
            self._sync_nonlinear_control_page
        )
        self.adaptive.toggled.connect(self._sync_increment_controls)
        self.regularize_zero_rows.toggled.connect(
            self.regularization_alpha.setEnabled
        )
        self._sync_nonlinear_control_page()
        self._sync_increment_controls()
        self.regularization_alpha.setEnabled(self.regularize_zero_rows.isChecked())
        return tabs

    def _build_load_control_page(self, settings):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.time_period = self._number(
            settings.get("time_period", self.step.time_period), 1e-15, 1.0e15
        )
        self.initial_increment = self._number(
            settings.get("initial_increment", 0.1), 1e-15, 1.0e15
        )
        self.minimum_increment = self._number(
            settings.get("minimum_increment", 1e-6), 0.0, 1.0e15
        )
        self.maximum_increment = self._number(
            settings.get("maximum_increment", 0.1), 1e-15, 1.0e15
        )
        layout.addWidget(
            field_row(
                field_block("Total load period", self.time_period),
                field_block("Initial increment", self.initial_increment),
            )
        )
        layout.addWidget(
            field_row(
                field_block("Minimum increment", self.minimum_increment),
                field_block("Maximum increment", self.maximum_increment),
            )
        )
        return page

    def _build_path_control_page(self, settings):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        self.total_arc_length = self._number(
            settings.get("total_arc_length", 1.0), 1e-15, 1.0e15
        )
        self.initial_arc_length = self._number(
            settings.get("initial_arc_length", settings.get("initial_increment", 0.05)),
            1e-15,
            1.0e15,
        )
        self.minimum_arc_length = self._number(
            settings.get("minimum_arc_length", settings.get("minimum_increment", 1e-5)),
            0.0,
            1.0e15,
        )
        self.maximum_arc_length = self._number(
            settings.get("maximum_arc_length", settings.get("maximum_increment", 0.1)),
            1e-15,
            1.0e15,
        )
        self.arc_length_psi = self._number(
            settings.get("arc_length_psi", 1.0), 0.0, 1.0e12
        )
        layout.addWidget(
            field_row(
                field_block("Estimated total arc length", self.total_arc_length),
                field_block("Initial arc length", self.initial_arc_length),
            )
        )
        layout.addWidget(
            field_row(
                field_block("Minimum arc length", self.minimum_arc_length),
                field_block("Maximum arc length", self.maximum_arc_length),
                field_block("Path load weighting (ψ)", self.arc_length_psi),
            )
        )
        return page

    @staticmethod
    def _number(value, minimum, maximum):
        editor = QDoubleSpinBox()
        editor.setRange(float(minimum), float(maximum))
        editor.setDecimals(12)
        editor.setValue(float(value))
        editor.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        apply_primary_control_height(editor)
        return editor

    @staticmethod
    def _integer(value, minimum, maximum):
        editor = QSpinBox()
        editor.setRange(int(minimum), int(maximum))
        editor.setValue(int(value))
        apply_primary_control_height(editor)
        return editor

    def _sync_nonlinear_control_page(self, *_):
        path = self.nonlinear_control.currentData() == "PATH"
        self.control_stack.setCurrentIndex(1 if path else 0)

    def _sync_increment_controls(self, *_):
        adaptive = self.adaptive.isChecked()
        for editor in (
            self.minimum_increment,
            self.maximum_increment,
            self.minimum_arc_length,
            self.maximum_arc_length,
            self.growth_factor,
            self.cutback_factor,
            self.fast_iterations,
            self.slow_iterations,
            self.maximum_cutbacks,
        ):
            editor.setEnabled(adaptive)

    def _accept(self) -> None:
        """Validate unique naming and nonlinear increment consistency."""
        from opencae.model.naming import is_unique

        if not is_unique(self.name.text(), self.existing_names, self.step.name):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A step named '{self.name.text().strip()}' already exists.",
            )
            return
        if self.step.step_type == "Nonlinear Static":
            path = self.nonlinear_control.currentData() == "PATH"
            minimum = (
                self.minimum_arc_length.value()
                if path
                else self.minimum_increment.value()
            )
            initial = (
                self.initial_arc_length.value()
                if path
                else self.initial_increment.value()
            )
            maximum = (
                self.maximum_arc_length.value()
                if path
                else self.maximum_increment.value()
            )
            if self.adaptive.isChecked() and not minimum <= initial <= maximum:
                QMessageBox.warning(
                    self,
                    "Invalid increments",
                    "Minimum, initial, and maximum increment sizes must be ordered.",
                )
                return
        self.accept()

    def _nonlinear_values(self):
        settings = dict(self.step.settings or {})
        settings.update(
            {
                "control": str(self.nonlinear_control.currentData()),
                "adaptive": self.adaptive.isChecked(),
                "max_increments": self.max_increments.value(),
                "max_iterations": self.max_iterations.value(),
                "tolerance": self.tolerance.value(),
                "growth_factor": self.growth_factor.value(),
                "cutback_factor": self.cutback_factor.value(),
                "fast_iterations": self.fast_iterations.value(),
                "slow_iterations": self.slow_iterations.value(),
                "maximum_cutbacks": self.maximum_cutbacks.value(),
                "regularize_zero_rows": self.regularize_zero_rows.isChecked(),
                "regularization_alpha": self.regularization_alpha.value(),
                "initial_increment": self.initial_increment.value(),
                "minimum_increment": self.minimum_increment.value(),
                "maximum_increment": self.maximum_increment.value(),
                "total_arc_length": self.total_arc_length.value(),
                "initial_arc_length": self.initial_arc_length.value(),
                "minimum_arc_length": self.minimum_arc_length.value(),
                "maximum_arc_length": self.maximum_arc_length.value(),
                "arc_length_psi": self.arc_length_psi.value(),
            }
        )
        return settings

    def values(self) -> dict:
        """Return edited step settings and IDs of all checked entities."""
        result = {
            "name": self.name.text().strip(),
            "number_of_modes": self.modes.value(),
            "support_ids": self.supports.selected_values(),
            "load_ids": self.loads.selected_values() if self.loads else [],
        }
        if self.step.step_type == "Nonlinear Static":
            result["time_period"] = self.time_period.value()
            result["settings"] = self._nonlinear_values()
        return result
