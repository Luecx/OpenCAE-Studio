"""Regression coverage for startup, material, seed, and assembly workflow polish."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QDialogButtonBox

from opencae.app.startup_window import StartupWindow
from opencae.model.entities.resources.material_library import material_from_preset
from opencae.ui.dialogs.default_seed import DefaultSeedDialog
from opencae.ui.viewport.stage_guidance import assembly_guidance
from opencae.units.system import UnitSystem


ROOT = Path(__file__).resolve().parents[1]


def test_application_module_defers_main_window_import():
    """Importing the launcher must not pull the heavy viewport/MainWindow stack."""
    environment = dict(os.environ)
    environment.setdefault("QT_QPA_PLATFORM", "offscreen")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "import opencae.app.application; "
                "assert 'opencae.app.main_window' not in sys.modules"
            ),
        ],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_startup_surface_does_not_behave_like_focus_stealing_tool_window():
    """Startup feedback must not restack the desktop like an always-on-top tool."""
    app = QApplication.instance() or QApplication([])
    startup = StartupWindow()
    try:
        flags = startup.windowFlags()
        assert (
            flags & Qt.WindowType.WindowType_Mask
        ) == Qt.WindowType.SplashScreen
        assert flags & Qt.WindowType.WindowDoesNotAcceptFocus
        assert not (flags & Qt.WindowType.WindowStaysOnTopHint)
        assert startup.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        assert startup.focusPolicy() == Qt.FocusPolicy.NoFocus
    finally:
        startup.deleteLater()
        app.processEvents()

    application_source = (ROOT / "opencae/app/application.py").read_text(
        encoding="utf-8"
    )
    startup_source = (ROOT / "opencae/app/startup_window.py").read_text(
        encoding="utf-8"
    )
    assert application_source.index("startup.hide()") < application_source.index(
        "window.show()"
    )
    assert "WindowStaysOnTopHint" not in startup_source
    assert "Qt.WindowType.Tool," not in startup_source


def test_structural_steel_preset_converts_to_active_units():
    """Built-in SI data is converted into the project's consistent unit system."""
    units = UnitSystem(
        "mm-N-s-°C",
        length="mm",
        force="N",
        time="s",
        temperature="°C",
    )
    material = material_from_preset("Structural Steel", units)

    assert material.youngs_modulus == pytest.approx(200_000.0)
    assert material.poisson_ratio == pytest.approx(0.3)
    assert material.density == pytest.approx(7.85e-9)
    assert len(material.behaviors) == 2


def test_assembly_guidance_only_appears_without_active_instances(project_factory):
    """Assembly-dependent stages explain the prerequisite instead of showing empty space."""
    project = project_factory(include_constraints=False)["project"]
    assert assembly_guidance("CONSTRAINTS", project) is None

    project.assembly.instances.clear()
    title, body = assembly_guidance("CONSTRAINTS", project)
    assert "no active instances" in title.lower()
    assert "Create an assembly instance" in body
    assert assembly_guidance("ASSEMBLY", project) is not None
    assert assembly_guidance("PART", project) is None


def test_seed_part_dialog_has_apply_ok_and_cancel():
    """Seed Part supports preview-style Apply plus conventional OK/Cancel."""
    app = QApplication.instance() or QApplication([])
    dialog = DefaultSeedDialog()
    buttons = dialog.findChild(QDialogButtonBox)
    assert buttons is not None
    assert buttons.button(QDialogButtonBox.StandardButton.Apply) is not None
    assert buttons.button(QDialogButtonBox.StandardButton.Ok) is not None
    assert buttons.button(QDialogButtonBox.StandardButton.Cancel) is not None
    dialog.close()
    assert app is not None
