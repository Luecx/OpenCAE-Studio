"""Regression coverage for deterministic result loading and tree synchronization."""

from PyQt6.QtCore import QObject, Qt, pyqtSignal
from PyQt6.QtWidgets import QApplication

from opencae.model.entities.jobs import ResultField, ResultSet
from opencae.ui.ribbon.result_field_menu import ResultFieldButton
from opencae.ui.tree.solution_tree import SolutionTree


class _Store(QObject):
    changed = pyqtSignal()
    message = pyqtSignal(str)

    def __init__(self, result):
        super().__init__()
        self.project = type("Project", (), {"results": [result]})()


def _field(name, step, frame, components=("D1", "D2", "D3")):
    return ResultField(
        name=name,
        location="Nodal",
        components=len(components),
        metadata={
            "step_id": step,
            "frame_id": frame,
            "frame_value": float(frame - 1),
            "components": list(components),
            "derived": [],
        },
    )


def test_result_load_defaults_to_first_step_frame_and_field_and_reveals_tree_item():
    app = QApplication.instance() or QApplication([])
    fields = [
        _field("STRESS", 2, 1),
        _field("TEMP", 1, 2, ("T",)),
        _field("DISP", 1, 1),
        _field("STRESS", 1, 1),
    ]
    result = ResultSet(name="Imported FRD", fields=fields)
    selector = ResultFieldButton()
    tree = SolutionTree(_Store(result))
    try:
        selector.set_solution(result, fields)
        selected = selector.current_field()

        assert selector.step.currentData() == 1
        assert selector.frame.currentData()[0] == 1
        assert selector.field.currentText() == "DISP"
        assert selector.component.currentText() == "Magnitude"
        assert selected is not None
        assert selected.name == "DISP"
        assert selected.metadata["component"] == "Magnitude"

        tree.select_solution(result, selected)
        index = tree.currentIndex()
        current = index.data(Qt.ItemDataRole.UserRole + 1)
        assert index.isValid()
        assert index.data(Qt.ItemDataRole.DisplayRole) == "DISP"
        assert current is not None
        assert current.name == "DISP"
        assert current.metadata["component"] == "Magnitude"
        assert tree.isExpanded(index.parent())
        assert tree.isExpanded(index.parent().parent())
        assert tree.isExpanded(index.parent().parent().parent())
    finally:
        tree.deleteLater()
        selector.deleteLater()
        app.processEvents()
