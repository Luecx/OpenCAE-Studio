"""Regression coverage for workflow ribbon, context menu and dialog behavior."""

import ast
from pathlib import Path
from types import SimpleNamespace

from PyQt6.QtCore import QPointF, QTimer, Qt
from PyQt6.QtWidgets import QApplication, QDialog

from opencae.deck_formats.selection import builtin_profile_id
from opencae.model.core import EntityRef
from opencae.model.entities.analysis import Analysis, AnalysisStep
from opencae.solvers.registry import available_solvers
from opencae.ui.core.icons.factory import _ICON_MAP, _x_icon, make_icon
from opencae.ui.core.icons.kinds import IconKind
from opencae.ui.dialogs.analysis_dialog import AnalysisDialog
from opencae.ui.viewport.click_gesture import ClickGestureTracker
from opencae.ui.visibility_state import VisibilityState


ROOT = Path(__file__).resolve().parents[1]


def _ribbon_groups(relative_path):
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    module = ast.parse(source)
    groups = []
    for node in ast.walk(module):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        name = function.id if isinstance(function, ast.Name) else getattr(function, "attr", "")
        if name != "RibbonGroupSpec" or len(node.args) < 2:
            continue
        title = ast.literal_eval(node.args[0])
        actions = tuple(
            item.attr
            for item in node.args[1].elts
            if isinstance(item, ast.Attribute)
        )
        groups.append((title, actions))
    return groups


def test_executable_selector_contains_only_dropdown_and_title():
    source = (
        ROOT / "opencae/ui/core/widgets/entity_selector_bar.py"
    ).read_text(encoding="utf-8")

    assert "QVBoxLayout(self)" in source
    assert 'label.setObjectName("RibbonGroupTitle")' in source
    assert "layout.addWidget(self.selector)" in source
    assert "layout.addWidget(label)" in source
    assert source.index("layout.addWidget(self.selector)") < source.index(
        "layout.addWidget(label)"
    )
    assert "action_button" not in source
    assert "action_ids" not in source


def test_analysis_ribbon_separates_definition_and_execution_groups():
    assert _ribbon_groups("opencae/ui/ribbon/analysis_page.py") == [
        (
            "DEFINITION",
            ("ANALYSIS_NEW", "ANALYSIS_EDIT", "DELETE_SELECTED"),
        ),
        (
            "ANALYSIS",
            (
                "VALIDATE",
                "PREVIEW_DECK",
                "WRITE_DECK",
                "SOLVER_SETTINGS",
                "ANALYSIS_RUN",
            ),
        ),
    ]


def test_studies_ribbon_separates_definition_setup_and_execution_groups():
    assert _ribbon_groups("opencae/ui/ribbon/studies_page.py") == [
        (
            "DEFINITION",
            ("STUDY_NEW_TOPOLOGY", "STUDY_EDIT", "DELETE_SELECTED"),
        ),
        (
            "TOPOLOGY SETUP",
            (
                "OPT_RESPONSE",
                "OPT_OBJECTIVE",
                "OPT_CONSTRAINT",
                "OPT_FILTER",
                "OPT_SYMMETRY",
                "OPT_CONTROLS",
            ),
        ),
        (
            "STUDY",
            ("STUDY_VALIDATE", "STUDY_RUN"),
        ),
    ]


def test_steps_ribbon_does_not_expose_selected_edit_or_delete():
    source = (ROOT / "opencae/ui/ribbon/steps_page.py").read_text(
        encoding="utf-8"
    )

    assert "A.REORDER_STEPS" in source
    assert "A.STEP_MATRIX" in source
    assert "A.EDIT_SELECTED" not in source
    assert "A.DELETE_SELECTED" not in source


def test_context_menu_keeps_unavailable_actions_visible_but_disabled():
    source = (ROOT / "opencae/ui/tree/context_menu.py").read_text(
        encoding="utf-8"
    )

    assert "ids = tuple(MAP.get(kind, ()))" in source
    assert "action.setEnabled(bool(enabled and source.isEnabled()))" in source
    assert "available(action_id, store, kind)" in source
    assert "if available(action_id, store, kind)" not in source


def test_delete_uses_the_canonical_close_glyph():
    app = QApplication.instance() or QApplication([])
    size = 32
    actual = make_icon(IconKind.DELETE, size).pixmap(size, size).toImage()
    expected = _x_icon(size).pixmap(size, size).toImage()

    assert actual == expected
    assert IconKind.DELETE not in _ICON_MAP


def test_analysis_dialog_remains_usable_after_exec_returns():
    app = QApplication.instance() or QApplication([])
    step = AnalysisStep(name="Static", step_type="Linear Static")
    analysis = Analysis(
        name="Analysis-1",
        step_refs=[EntityRef.of(step, "AnalysisStep")],
    )
    settings = SimpleNamespace(deck_profiles={})
    dialog = AnalysisDialog(
        analysis,
        [step],
        available_solvers(),
        settings,
        existing_names=(),
    )

    QTimer.singleShot(0, dialog.accept)
    result = dialog.exec()

    assert result == QDialog.DialogCode.Accepted
    assert dialog.validate()
    candidate = dialog.result()
    assert candidate.name == "Analysis-1"
    assert candidate.solver == "FEMaster"
    assert candidate.deck_profile_id == builtin_profile_id("FEMaster")
    assert [reference.entity_id for reference in candidate.step_refs] == [step.id]
    dialog.deleteLater()
    app.processEvents()


class _MouseEvent:
    """Small Qt-event stand-in for deterministic click-gesture tests."""

    def __init__(self, x, y, *, button=None, buttons=None):
        self._point = QPointF(float(x), float(y))
        self._button = button or Qt.MouseButton.NoButton
        self._buttons = buttons or Qt.MouseButton.NoButton

    def globalPosition(self):
        return self._point

    def button(self):
        return self._button

    def buttons(self):
        return self._buttons


def test_viewport_click_tracker_rejects_camera_drag_release():
    """A left-button camera drag must never be reinterpreted as a pick click."""
    tracker = ClickGestureTracker(drag_threshold=4.0)
    tracker.press(
        _MouseEvent(100, 100, button=Qt.MouseButton.LeftButton)
    )
    tracker.move(
        _MouseEvent(
            118,
            103,
            buttons=Qt.MouseButton.LeftButton,
        )
    )

    assert not tracker.release_is_click(
        _MouseEvent(118, 103, button=Qt.MouseButton.LeftButton)
    )


def test_viewport_click_tracker_accepts_stationary_release():
    """A normal stationary left click must still reach the active picker."""
    tracker = ClickGestureTracker(drag_threshold=4.0)
    tracker.press(
        _MouseEvent(100, 100, button=Qt.MouseButton.LeftButton)
    )

    assert tracker.release_is_click(
        _MouseEvent(102, 101, button=Qt.MouseButton.LeftButton)
    )


def test_visibility_state_emits_topology_scope_without_entity_invalidation():
    """Face visibility changes identify their Part/category for the fast path."""
    state = VisibilityState(SimpleNamespace(id="project"))
    topology = []
    entities = []
    state.topology_changed.connect(
        lambda owner, kind: topology.append((owner, kind))
    )
    state.entity_changed.connect(entities.append)

    state.hide_topology("part-1", "face", (7,))

    assert topology == [("part-1", "faces")]
    assert entities == []
    assert state.hidden_topology("part-1", "faces") == frozenset({7})
