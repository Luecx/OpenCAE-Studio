from __future__ import annotations

from copy import deepcopy

from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from opencae.model.entities.optimization import (
    FilterRadius,
    SymmetryType,
    TopologyControls,
    TopologyFilterSettings,
    TopologySymmetry,
)

from .optimization_common import EntityDialog, double_spin


class RadiusEditor(QWidget):
    def __init__(self, value: FilterRadius, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.automatic = QRadioButton(
            "Automatic from minimum element spacing"
        )
        self.manual = QRadioButton("Manual distance")
        self.factor = QDoubleSpinBox()
        self.factor.setDecimals(4)
        self.factor.setRange(1.0, 1000.0)
        self.factor.setValue(float(value.factor))
        self.distance = QDoubleSpinBox()
        self.distance.setDecimals(9)
        self.distance.setRange(1.0e-12, 1.0e30)
        self.distance.setValue(max(float(value.value), 1.0e-12))
        self.automatic.setChecked(value.automatic)
        self.manual.setChecked(not value.automatic)
        self.automatic.toggled.connect(self._sync)
        self.manual.toggled.connect(self._sync)
        layout.addRow(self.automatic)
        layout.addRow("Factor × minimum distance", self.factor)
        layout.addRow(self.manual)
        layout.addRow("Distance", self.distance)
        self._sync()

    def _sync(self, *_):
        self.factor.setEnabled(self.automatic.isChecked())
        self.distance.setEnabled(self.manual.isChecked())

    def result(self):
        return FilterRadius(
            automatic=self.automatic.isChecked(),
            factor=self.factor.value(),
            value=self.distance.value(),
        )


class TopologyFilterDialog(EntityDialog):
    def __init__(self, value: TopologyFilterSettings, parent=None):
        super().__init__("Topology Filters", parent)
        self.value = deepcopy(value)
        self.setMinimumWidth(590)
        form = QFormLayout()
        self.name = QLineEdit(self.value.name)
        self.enabled = QCheckBox("Enable filtering")
        self.enabled.setChecked(self.value.enabled)
        self.weighted = QCheckBox("Density-weighted sensitivity filter")
        self.weighted.setChecked(self.value.density_weighted_sensitivities)
        form.addRow("Name", self.name)
        form.addRow("", self.enabled)
        form.addRow("", self.weighted)
        self.root.addLayout(form)

        density_group = QGroupBox(
            "Density / constraint coupling radius — local"
        )
        density_layout = QVBoxLayout(density_group)
        density_note = QLabel(
            "Builds the physical-density and symmetry coupling matrix. "
            "Automatic default: 2.5 × the minimum positive centroid distance."
        )
        density_note.setWordWrap(True)
        density_note.setObjectName("MutedLabel")
        self.density_radius = RadiusEditor(
            self.value.density_constraint_radius
        )
        density_layout.addWidget(density_note)
        density_layout.addWidget(self.density_radius)
        self.root.addWidget(density_group)

        sensitivity_group = QGroupBox(
            "Sensitivity-filter radius — broader"
        )
        sensitivity_layout = QVBoxLayout(sensitivity_group)
        sensitivity_note = QLabel(
            "Filters compliance sensitivities only. It is intentionally larger "
            "than the density/constraint radius. Automatic default: 5 × the "
            "minimum positive centroid distance."
        )
        sensitivity_note.setWordWrap(True)
        sensitivity_note.setObjectName("MutedLabel")
        self.sensitivity_radius = RadiusEditor(self.value.sensitivity_radius)
        sensitivity_layout.addWidget(sensitivity_note)
        sensitivity_layout.addWidget(self.sensitivity_radius)
        self.root.addWidget(sensitivity_group)
        self.finish()

    def result(self):
        candidate = deepcopy(self.value)
        candidate.name = self.name.text().strip() or candidate.name
        candidate.enabled = self.enabled.isChecked()
        candidate.density_weighted_sensitivities = self.weighted.isChecked()
        candidate.density_constraint_radius = self.density_radius.result()
        candidate.sensitivity_radius = self.sensitivity_radius.result()
        return candidate


class TopologySymmetryDialog(EntityDialog):
    def __init__(
        self,
        value=None,
        *,
        pick_reference=None,
        clear_preview=None,
        parent=None,
    ):
        super().__init__("Topology Symmetry", parent)
        self.value = deepcopy(value) if value else TopologySymmetry(
            name="Symmetry-1"
        )
        self.pick_reference = pick_reference
        self.clear_preview = clear_preview
        self.reference = dict(self.value.reference)
        form = QFormLayout()
        self.name = QLineEdit(self.value.name)
        self.kind = QComboBox()
        self.kind.addItem("Planar", SymmetryType.PLANAR.value)
        self.kind.addItem("Rotational", SymmetryType.ROTATIONAL.value)
        current = self.kind.findData(self.value.symmetry_type.value)
        self.kind.setCurrentIndex(max(current, 0))
        self.kind.currentIndexChanged.connect(self._kind_changed)
        self.reference_label = QLineEdit()
        self.reference_label.setReadOnly(True)
        self.pick = QPushButton("Pick Reference")
        self.pick.setCheckable(True)
        self.pick.toggled.connect(self._pick)
        reference_row = QWidget()
        row = QHBoxLayout(reference_row)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.reference_label, 1)
        row.addWidget(self.pick)
        self.occurrences = QSpinBox()
        self.occurrences.setRange(2, 128)
        self.occurrences.setValue(self.value.occurrences)
        self.enabled = QCheckBox("Enabled")
        self.enabled.setChecked(self.value.enabled)
        form.addRow("Name", self.name)
        form.addRow("Type", self.kind)
        form.addRow("Reference", reference_row)
        form.addRow("Occurrences", self.occurrences)
        form.addRow("", self.enabled)
        self.root.addLayout(form)
        self.finished.connect(lambda _code: self._cleanup())
        self._refresh_reference()
        self._kind_changed()
        self.finish()

    def _kind_changed(self, *_):
        planar = self.kind.currentData() == SymmetryType.PLANAR.value
        self.occurrences.setEnabled(not planar)
        if planar:
            self.occurrences.setValue(2)
        expected = (
            {"face", "datum_plane"}
            if planar
            else {"edge", "datum_vector"}
        )
        if self.reference and self.reference.get("kind") not in expected:
            self.reference = {}
            self._refresh_reference()
            if self.clear_preview:
                self.clear_preview()

    def _pick(self, active):
        if not active:
            return
        if self.pick_reference is None:
            self.pick.setChecked(False)
            return
        self.pick_reference(
            SymmetryType(self.kind.currentData()),
            self._reference_picked,
            self._pick_finished,
        )

    def _reference_picked(self, reference):
        self.reference = dict(reference or {})
        self._refresh_reference()

    def _pick_finished(self):
        self.pick.setChecked(False)

    def _refresh_reference(self):
        self.reference_label.setText(
            str(
                self.reference.get("name")
                or self.reference.get("kind")
                or "Nothing selected"
            )
        )

    def _cleanup(self):
        if self.clear_preview:
            self.clear_preview()

    def result(self):
        candidate = deepcopy(self.value)
        candidate.name = self.name.text().strip() or candidate.name
        candidate.symmetry_type = SymmetryType(self.kind.currentData())
        candidate.reference = dict(self.reference)
        candidate.occurrences = (
            2
            if candidate.symmetry_type == SymmetryType.PLANAR
            else self.occurrences.value()
        )
        candidate.enabled = self.enabled.isChecked()
        return candidate


class TopologyControlsDialog(EntityDialog):
    def __init__(self, value: TopologyControls, parent=None):
        super().__init__("Topology Optimization Controls", parent)
        self.value = deepcopy(value)
        self.setMinimumWidth(470)
        form = QFormLayout()
        self.name = QLineEdit(self.value.name)
        self.iterations = QSpinBox()
        self.iterations.setRange(1, 100000)
        self.iterations.setValue(self.value.maximum_iterations)
        self.minimum = double_spin(
            self.value.minimum_density, 1.0e-9, 0.999999, 9
        )
        self.initial = double_spin(
            self.value.initial_density, 1.0e-9, 1.0, 6
        )
        self.exponent = double_spin(
            self.value.simp_exponent, 0.01, 100.0, 6
        )
        self.move = double_spin(self.value.move_limit, 1.0e-6, 1.0, 6)
        self.density_tol = double_spin(
            self.value.density_change_tolerance, 1.0e-12, 1.0, 9
        )
        self.objective_tol = double_spin(
            self.value.objective_tolerance, 1.0e-12, 1.0, 9
        )
        self.bisection_tol = double_spin(
            self.value.bisection_tolerance, 1.0e-15, 1.0, 12
        )
        self.bisection_steps = QSpinBox()
        self.bisection_steps.setRange(1, 10000)
        self.bisection_steps.setValue(self.value.maximum_bisection_steps)
        self.save_every = QSpinBox()
        self.save_every.setRange(1, 10000)
        self.save_every.setValue(self.value.save_every)
        self.keep_files = QCheckBox("Keep FEMaster .res/.frd files")
        self.keep_files.setChecked(self.value.keep_solver_files)
        for label, widget in (
            ("Name", self.name),
            ("Maximum iterations", self.iterations),
            ("Minimum density", self.minimum),
            ("Initial density", self.initial),
            ("SIMP exponent", self.exponent),
            ("Move limit", self.move),
            ("Density-change tolerance", self.density_tol),
            ("Objective tolerance", self.objective_tol),
            ("Bisection tolerance", self.bisection_tol),
            ("Maximum bisection steps", self.bisection_steps),
            ("Save every N iterations", self.save_every),
            ("", self.keep_files),
        ):
            form.addRow(label, widget)
        self.root.addLayout(form)
        self.finish()

    def result(self):
        candidate = deepcopy(self.value)
        candidate.name = self.name.text().strip() or candidate.name
        candidate.maximum_iterations = self.iterations.value()
        candidate.minimum_density = self.minimum.value()
        candidate.initial_density = self.initial.value()
        candidate.simp_exponent = self.exponent.value()
        candidate.move_limit = self.move.value()
        candidate.density_change_tolerance = self.density_tol.value()
        candidate.objective_tolerance = self.objective_tol.value()
        candidate.bisection_tolerance = self.bisection_tol.value()
        candidate.maximum_bisection_steps = self.bisection_steps.value()
        candidate.save_every = self.save_every.value()
        candidate.keep_solver_files = self.keep_files.isChecked()
        return candidate
