"""Architecture guards for the flat OpenCAE UI primitive layer."""

from __future__ import annotations

import ast
from pathlib import Path


_REPO_ROOT = Path(__file__).resolve().parents[1]
_UI_ROOT = _REPO_ROOT / "opencae" / "ui"
_PRIMITIVES_ROOT = _UI_ROOT / "primitives"
_STYLES_ROOT = _UI_ROOT / "core" / "styles"

# Ordinary interactive controls must be instantiated through a concrete
# structurally named primitive. Framework containers/views such as QWidget,
# QFrame, QDialogButtonBox, QButtonGroup, QTableWidget and QTreeWidget remain
# valid composition tools outside the primitive layer.
_FORBIDDEN_DIRECT_CONTROLS = {
    "QPushButton",
    "QToolButton",
    "QLineEdit",
    "QSpinBox",
    "QDoubleSpinBox",
    "QComboBox",
    "QCheckBox",
    "QRadioButton",
    "QSlider",
    "QPlainTextEdit",
}

# Theme/style modules are a bootstrap dependency of the whole UI. They may use
# core tokens/metrics, but must never import higher-level widget construction
# packages or theme initialization becomes cyclic.
_FORBIDDEN_STYLE_IMPORT_PREFIXES = (
    "opencae.ui.templates",
    "opencae.ui.composites",
    "opencae.ui.primitives",
)

# These were transitional generic/Sketch-only widget abstractions. Reintroducing
# one would recreate the parallel hierarchy this refactor intentionally removed.
_FORBIDDEN_LEGACY_NAMES = {
    "ActionButton",
    "ButtonPresentation",
    "ChoiceButton",
    "FormButton",
    "InlineButton",
    "MenuButton",
    "OptionsButton",
    "SplitButton",
    "ToggleButton",
    "ViewportButton",
    "SemanticLabel",
    "BooleanInput",
    "ChoiceInput",
    "IntegerInput",
    "NumberInput",
    "TextInput",
    "ButtonSketchAction",
    "CheckSketch",
    "InputSketchNumber",
    "InputSketchText",
    "SelectSketch",
    "LabelSketchField",
    "LabelSketchHeading",
    "LabelSketchHint",
    "LabelSketchNote",
    "LabelSketchStatus",
    "ListSketchConstraints",
    "ControlSketchCommitButtons",
    "PanelSketchInspector",
}

_FORBIDDEN_LEGACY_FILES = {
    "action_button.py",
    "base.py",
    "choice_button.py",
    "factory.py",
    "form_button.py",
    "inline_button.py",
    "menu_button.py",
    "options_button.py",
    "presentation.py",
    "role.py",
    "selection_button.py",
    "spec.py",
    "split_button.py",
    "toggle_button.py",
    "viewport_button.py",
    "button_sketch_action.py",
    "check_sketch.py",
    "input_sketch_number.py",
    "input_sketch_text.py",
    "select_sketch.py",
    "list_sketch_constraints.py",
    "control_sketch_commit_buttons.py",
    "panel_sketch_inspector.py",
    "semantic_label.py",
    "boolean_input.py",
    "choice_input.py",
    "integer_input.py",
    "number_input.py",
    "text_input.py",
}


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _ui_files():
    return tuple(sorted(_UI_ROOT.rglob("*.py")))


def _relative(path: Path) -> str:
    return path.relative_to(_REPO_ROOT).as_posix()


def test_ui_consumers_construct_standard_controls_through_primitives():
    violations: list[str] = []
    for path in _ui_files():
        if path == _PRIMITIVES_ROOT or _PRIMITIVES_ROOT in path.parents:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node.func)
            if name in _FORBIDDEN_DIRECT_CONTROLS:
                violations.append(f"{_relative(path)}:{node.lineno}: {name}()")

    assert not violations, (
        "UI consumers must instantiate structurally named primitives instead of "
        "ordinary Qt controls:\n" + "\n".join(violations)
    )


def test_theme_style_modules_do_not_depend_on_widget_layers():
    violations: list[str] = []
    for path in sorted(_STYLES_ROOT.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                module = node.module
                if module.startswith(_FORBIDDEN_STYLE_IMPORT_PREFIXES):
                    violations.append(
                        f"{_relative(path)}:{node.lineno}: imports {module}"
                    )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(_FORBIDDEN_STYLE_IMPORT_PREFIXES):
                        violations.append(
                            f"{_relative(path)}:{node.lineno}: imports {alias.name}"
                        )

    assert not violations, (
        "Theme/style modules are bootstrap code and must depend only on core "
        "tokens/metrics, never templates/composites/primitives:\n"
        + "\n".join(violations)
    )


def test_removed_ui_widget_hierarchies_do_not_return():
    violations: list[str] = []
    for path in _ui_files():
        if path.name in _FORBIDDEN_LEGACY_FILES:
            violations.append(f"legacy file exists: {_relative(path)}")

        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in _FORBIDDEN_LEGACY_NAMES:
                        violations.append(
                            f"{_relative(path)}:{node.lineno}: imports {alias.name}"
                        )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    tail = alias.name.rsplit(".", 1)[-1]
                    if tail in _FORBIDDEN_LEGACY_NAMES:
                        violations.append(
                            f"{_relative(path)}:{node.lineno}: imports {alias.name}"
                        )
            elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_LEGACY_NAMES:
                violations.append(
                    f"{_relative(path)}:{node.lineno}: references {node.id}"
                )

    assert not violations, (
        "Removed generic or Sketch-only widget abstractions must not return:\n"
        + "\n".join(sorted(set(violations)))
    )
