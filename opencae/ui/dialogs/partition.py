from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.model.selection import RegionDefinition, local_geometry_tags
from opencae.model.entities.geometry import PartitionEdgeFeature, PartitionFaceFeature
from opencae.ui.core.widgets import ChevronComboBox, PointSelectionWidget, ReferenceSelector, CompactRegionSelector

PARTITION_TYPES = (
    "Cell by plane",
    "Face by two points",
    "Edge at parameter",
    "Edge at vertex",
)


class PartitionDialog(QDialog):
    committed = pyqtSignal(object)

    def __init__(
        self,
        project,
        part,
        point_provider,
        feature=None,
        parent=None,
        *,
        region_options=(),
        pick_callback=None,
        datum_planes=(),
        create_datum_plane=None,
    ):
        super().__init__(parent)
        self.project = project
        self.part_id = part.id
        self.point_provider = point_provider
        self.feature = feature
        self.region_options = tuple(region_options)
        self.pick_callback = pick_callback
        self.datum_planes = list(datum_planes)
        self.create_datum_plane = create_datum_plane
        self.setWindowTitle("Edit Partition" if feature else "Create Partition")
        self.setMinimumWidth(780)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 14)
        root.setSpacing(12)
        title = QLabel(self.windowTitle()); title.setObjectName("PanelTitle"); root.addWidget(title)
        form = QFormLayout()
        self.name = QLineEdit(getattr(feature, "name", "Partition-1"))
        self.kind = ChevronComboBox(); self.kind.addItems(PARTITION_TYPES)
        self.kind.setCurrentText(self._kind_from_feature(feature))
        form.addRow("History feature", self.name)
        form.addRow("Partition method", self.kind)
        root.addLayout(form)

        self.stack = QStackedWidget(); root.addWidget(self.stack)
        self._build_pages()
        self.kind.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.stack.setCurrentIndex(PARTITION_TYPES.index(self.kind.currentText()))
        self._load(feature)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setObjectName("PrimaryButton")
        buttons.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(lambda: self._commit(True))
        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(lambda: self._commit(False))
        buttons.rejected.connect(self.close)
        root.addWidget(buttons)

    def _target(self, dimension):
        callback = None
        if self.pick_callback:
            callback = lambda owner, done, finished, dim=dimension: self.pick_callback(dim, owner, done, finished)
        return CompactRegionSelector(
            self.project,
            RegionDefinition(),
            self.region_options,
            callback,
            parent=self,
            allow_part_local=True,
        )

    def _build_pages(self):
        plane = QWidget()
        form = QFormLayout(plane)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(9)
        self.plane_targets = self._target(3)
        self.datum_plane = ReferenceSelector(
            (("Select a datum plane", ""), *self.datum_planes),
            None,
            self._create_datum_plane if self.create_datum_plane else None,
            self._pick_datum_plane if self.pick_callback else None,
        )
        form.addRow("Target cell", self.plane_targets)
        form.addRow("Partition plane", self.datum_plane)
        self.stack.addWidget(plane)

        face = QWidget()
        form = QFormLayout(face)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(9)
        self.face_targets = self._target(2)
        self.face_points = PointSelectionWidget(selection_provider=self.point_provider)
        form.addRow("Target face", self.face_targets)
        form.addRow("Partition points", self.face_points)
        self.stack.addWidget(face)

        edge_parameter = QWidget()
        form = QFormLayout(edge_parameter)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(9)
        self.edge_parameter_targets = self._target(1)
        self.fraction = self._number(0.5)
        self.fraction.setRange(0.000001, 0.999999)
        form.addRow("Target edge", self.edge_parameter_targets)
        form.addRow("Normalized parameter", self.fraction)
        self.stack.addWidget(edge_parameter)

        edge_vertex = QWidget()
        form = QFormLayout(edge_vertex)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(9)
        self.edge_vertex_targets = self._target(1)
        self.edge_vertex = self._target(0)
        form.addRow("Target edge", self.edge_vertex_targets)
        form.addRow("Splitting vertex", self.edge_vertex)
        self.stack.addWidget(edge_vertex)

    @staticmethod
    def _number(value):
        editor = QDoubleSpinBox(); editor.setRange(-1e30, 1e30); editor.setDecimals(8); editor.setValue(value)
        return editor

    @staticmethod
    def _kind_from_feature(feature):
        if feature is None: return PARTITION_TYPES[0]
        if isinstance(feature, PartitionFaceFeature): return PARTITION_TYPES[1]
        if isinstance(feature, PartitionEdgeFeature):
            return PARTITION_TYPES[3] if feature.method == "Vertex" else PARTITION_TYPES[2]
        return PARTITION_TYPES[0]

    def _load(self, feature):
        if feature is None: return
        kind = self._kind_from_feature(feature)
        if kind == PARTITION_TYPES[0]:
            self.plane_targets.set_definition(feature.target)
            self.datum_plane.setCurrentValue(getattr(getattr(feature, "datum_plane_ref", None), "entity_id", ""))
        elif kind == PARTITION_TYPES[1]:
            self.face_targets.set_definition(feature.target)
            self.face_points.set_points(feature.points)
        elif kind == PARTITION_TYPES[2]:
            self.edge_parameter_targets.set_definition(feature.target)
            self.fraction.setValue(feature.fraction)
        else:
            self.edge_vertex_targets.set_definition(feature.target)
            self.edge_vertex.set_definition(getattr(feature, "split_target", RegionDefinition()))

    def values(self):
        kind = self.kind.currentText()
        base = {"name": self.name.text().strip(), "partition_type": kind}
        if kind == PARTITION_TYPES[0]:
            datum_id = self.datum_plane.currentValue()
            parameters = {"datum_plane_id": datum_id or ""}
            base.update(target=self.plane_targets.definition(), split_target=RegionDefinition(), values=parameters)
        elif kind == PARTITION_TYPES[1]:
            base.update(target=self.face_targets.definition(), split_target=RegionDefinition(), values={"points": self.face_points.points()})
        elif kind == PARTITION_TYPES[2]:
            base.update(
                target=self.edge_parameter_targets.definition(),
                split_target=RegionDefinition(),
                values={"method": "Parameter", "fraction": self.fraction.value()},
            )
        else:
            base.update(
                target=self.edge_vertex_targets.definition(),
                split_target=self.edge_vertex.definition(),
                values={"method": "Vertex"},
            )
        return base

    def _commit(self, close_after):
        values = self.values()
        if not values["name"]:
            QMessageBox.warning(self, "Invalid partition", "Enter a feature name."); return
        dimension = {PARTITION_TYPES[0]: 3, PARTITION_TYPES[1]: 2, PARTITION_TYPES[2]: 1, PARTITION_TYPES[3]: 1}[values["partition_type"]]
        part = self.project.try_resolve(self.part_id)
        if part is None:
            QMessageBox.warning(self, "Missing part", "The edited part no longer exists."); return
        tags = local_geometry_tags(part, values["target"], dimension)
        if len(tags) != 1:
            QMessageBox.warning(self, "Invalid target", f"Select exactly one geometry {('vertex','edge','face','cell')[dimension]}."); return
        if values["partition_type"] == PARTITION_TYPES[0] and not values["values"].get("datum_plane_id"):
            QMessageBox.warning(self, "Missing plane", "Select or create a datum plane for the partition."); return
        if values["partition_type"] == PARTITION_TYPES[1] and len(values["values"]["points"]) != 2:
            QMessageBox.warning(self, "Missing points", "Pick exactly two positions on the target face."); return
        if values["partition_type"] == PARTITION_TYPES[3] and len(local_geometry_tags(part, values["split_target"], 0)) != 1:
            QMessageBox.warning(self, "Missing vertex", "Select exactly one splitting vertex."); return
        self.committed.emit(values)
        if close_after: self.accept()

    def _pick_datum_plane(self, owner, done):
        if not self.pick_callback:
            return
        self.pick_callback("datum_plane", owner, done, lambda: self.datum_plane.pick_button.setChecked(False))

    def _create_datum_plane(self, owner, done):
        def created(value):
            if value is not None and value not in self.datum_planes: self.datum_planes.append(value)
            done(value)
        self.create_datum_plane(owner, created)
