"""Regression coverage for the UI-only input deck format manager prototype."""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture()
def manager():
    """Create one offscreen deck format manager and clean it up after each test."""
    qt_widgets = pytest.importorskip("PyQt6.QtWidgets")
    from opencae.ui.deck_format_manager import DeckFormatManagerDialog

    application = qt_widgets.QApplication.instance() or qt_widgets.QApplication([])
    dialog = DeckFormatManagerDialog()
    application.processEvents()
    yield dialog
    dialog.close()
    application.processEvents()


def test_primary_format_groups_are_not_wrapped_in_resources(manager):
    """Materials, sections and coordinate systems stay first-class tree groups."""
    labels = manager.navigation.top_level_labels()
    assert "Resources" not in labels
    assert "Materials" in labels
    assert "Sections" in labels
    assert "Profiles" in labels
    assert "Coordinate Systems" in labels


def test_move_buttons_reorder_selected_record_within_tree(manager):
    """Output ordering is edited directly in the left navigation hierarchy."""
    before = manager.navigation.child_labels("materials")
    assert before[:3] == ["Material Header", "Isotropic Elastic", "Density"]

    assert manager.navigation.select_key("materials.isotropic_elastic")
    manager.navigation.move_down()

    after = manager.navigation.child_labels("materials")
    assert after[:3] == ["Material Header", "Density", "Isotropic Elastic"]
    assert manager.navigation.current_key() == "materials.isotropic_elastic"


def test_isotropic_elastic_uses_one_template_and_documents_fields(manager):
    """Keyword options and data lines share one editor with explicit placeholders."""
    assert manager.select_key("materials.isotropic_elastic")
    page = manager.template_page

    assert manager.stack.currentWidget() is page
    assert page.template_text() == (
        "*ELASTIC, TYPE=ISO\n{youngs_modulus}, {poisson_ratio}"
    )
    assert page.available_field_names() == (
        "youngs_modulus",
        "poisson_ratio",
        "material_name",
        "temperature",
    )
    assert "*MATERIAL, NAME=STEEL" in page.preview.toPlainText()
    assert "*ELASTIC, TYPE=ISO" in page.preview.toPlainText()
    assert "210000, 0.3" in page.preview.toPlainText()

    checkboxes = [item.text() for item in page.findChildren(type(page.enabled))]
    assert checkboxes == ["Enabled"]


def test_available_field_can_be_inserted_at_template_cursor(manager):
    """The field helper inserts valid placeholders instead of requiring memorization."""
    from PyQt6.QtGui import QTextCursor

    manager.select_key("materials.isotropic_elastic")
    page = manager.template_page
    cursor = page.template.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.End)
    cursor.insertText("\nE=")
    page.template.setTextCursor(cursor)
    page.insert_field("youngs_modulus")

    assert page.template_text().endswith("E={youngs_modulus}")


def test_global_format_options_only_appear_under_general_settings(manager):
    """Formatter-wide options do not clutter record-specific template pages."""
    from PyQt6.QtWidgets import QCheckBox

    manager.select_key("general.formatting")
    assert manager.stack.currentWidget() is manager.global_page
    labels = [item.text() for item in manager.global_page.findChildren(QCheckBox)]
    assert "Uppercase generated keywords" in labels
    assert "Insert a blank line between top-level blocks" in labels
