"""Regression coverage for workflow ribbon, context menu and dialog behavior."""

from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QDialog

from opencae.model.core import EntityRef
from opencae.model.entities.analysis import Analysis, AnalysisStep
from opencae.ui.dialogs.analysis_dialog import AnalysisDialog


ROOT = Path(__file__).resolve().parents[1]


def test_executable_selector_matches_part_selector_layout_and_button_size():
    source = (
        ROOT / "opencae/ui/core/widgets/entity_selector_bar.py"
    ).read_text(encoding="utf-8")

    assert "QVBoxLayout(selector_panel)" in source
    assert 'label.setObjectName("RibbonGroupTitle")' in source
    assert "selector_layout.addWidget(self.selector)" in source
    assert "selector_layout.addWidget(label)" in source
    assert source.index("selector_layout.addWidget(self.selector)") < source.index(
        "selector_layout.addWidget(label)"
    )
    assert "action_button(actions.get(action_id))" in source
    assert "QToolButton" not in source


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


def test_delete_uses_a_real_trash_icon():
    source = (ROOT / "opencae/ui/core/icons/factory.py").read_text(
        encoding="utf-8"
    )

    assert "if kind == IconKind.DELETE" in source
    assert "QStyle.StandardPixmap.SP_TrashIcon" in source
    assert "IconKind.DELETE:LegacyKind.FIXED" not in source


def test_analysis_dialog_remains_usable_after_exec_returns():
    app = QApplication.instance() or QApplication([])
    step = AnalysisStep(name="Static", step_type="Linear Static")
    analysis = Analysis(
        name="Analysis-1",
        step_refs=[EntityRef.of(step, "AnalysisStep")],
    )
    dialog = AnalysisDialog(
        analysis,
        [step],
        ["FEMaster"],
        existing_names=(),
    )

    QTimer.singleShot(0, dialog.accept)
    result = dialog.exec()

    assert result == QDialog.DialogCode.Accepted
    assert dialog.validate()
    candidate = dialog.result()
    assert candidate.name == "Analysis-1"
    assert [reference.entity_id for reference in candidate.step_refs] == [step.id]
    dialog.deleteLater()
    app.processEvents()
