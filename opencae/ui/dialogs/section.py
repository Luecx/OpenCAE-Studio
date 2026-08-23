"""Provides Create/Edit Section with the shared label-above-control styling."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QGroupBox,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from opencae.model.core import EntityRef
from opencae.ui.core.apply_dialog import ApplyDialog
from opencae.ui.core.widgets import ChevronComboBox, MatrixEditor, ReferenceSelector
from opencae.ui.templates import (
    NumericUnitInput,
    apply_primary_control_height,
    dialog_buttons,
    field_block,
    field_row,
)

SECTION_TYPES = ("Solid", "Shell", "Beam", "Truss")
SHELL_TYPES = ("Integrated shell section", "ABD shell section")


class SectionDialog(ApplyDialog):
    """Create or edit all section variants with vertically labelled controls."""

    def __init__(
        self,
        materials=(),
        profiles=(),
        create_material=None,
        create_profile=None,
        section=None,
        existing_names=(),
        parent=None,
        initial_type=None,
        default_name="Section-1",
        units=None,
    ):
        super().__init__(parent)
        self.section = section
        self.units = units
        self.existing_names = {name.casefold() for name in existing_names}

        self.setWindowTitle("Edit Section" if section else "Create Section")
        self.setMinimumSize(760, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 18)
        root.setSpacing(16)

        self.name = QLineEdit(section.name if section else default_name)
        apply_primary_control_height(self.name)
        root.addWidget(field_block("Name", self.name))

        self.kind = ChevronComboBox()
        self.kind.setMinimumWidth(0)
        self.kind.addItems(SECTION_TYPES)
        self.kind.setCurrentText(
            section.section_type if section else (initial_type or "Solid")
        )
        apply_primary_control_height(self.kind)
        root.addWidget(field_block("Section type", self.kind))

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        material_current = (
            section.material_ref.entity_id if section and section.material_ref else ""
        )
        profile_current = (
            section.profile_ref.entity_id if section and section.profile_ref else ""
        )

        self.solid_material = self._reference_page(
            "Material",
            materials,
            material_current,
            create_material,
        )
        self.stack.addWidget(self.solid_material[0])

        self.shell_page = self._shell_page(
            materials,
            material_current,
            create_material,
        )
        self.stack.addWidget(self.shell_page)

        self.beam_page, self.beam_material, self.beam_profile = self._beam_page(
            materials,
            profiles,
            material_current,
            profile_current,
            create_material,
            create_profile,
        )
        self.stack.addWidget(self.beam_page)

        self.truss_page, self.truss_material, self.truss_area = self._truss_page(
            materials,
            material_current,
            create_material,
        )
        self.stack.addWidget(self.truss_page)

        buttons = dialog_buttons(include_apply=True)
        self.bind_buttons(buttons, True)
        root.addWidget(buttons)

        self.kind.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.kind.currentIndexChanged.connect(self._resize)
        self.stack.setCurrentIndex(SECTION_TYPES.index(self.kind.currentText()))

    @staticmethod
    def _vertical_page() -> tuple[QWidget, QVBoxLayout]:
        """Create a dynamic section page using the standard vertical rhythm."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        return page, layout

    @classmethod
    def _reference_page(cls, text, values, current, callback):
        """Create a page containing one labelled object-reference selector."""
        page, layout = cls._vertical_page()
        selector = ReferenceSelector(values, current, callback)
        layout.addWidget(field_block(text, selector))
        layout.addStretch(1)
        return page, selector

    def _shell_page(self, materials, current, callback):
        """Build integrated and ABD shell-section editors."""
        page, layout = self._vertical_page()

        self.shell_definition = ChevronComboBox()
        self.shell_definition.setMinimumWidth(0)
        self.shell_definition.addItems(SHELL_TYPES)
        self.shell_definition.setCurrentText(
            getattr(self.section, "shell_definition", SHELL_TYPES[0])
        )
        apply_primary_control_height(self.shell_definition)
        layout.addWidget(field_block("Shell formulation", self.shell_definition))

        self.shell_stack = QStackedWidget()
        layout.addWidget(self.shell_stack, 1)

        integrated, integrated_layout = self._vertical_page()
        self.shell_material = ReferenceSelector(materials, current, callback)
        self.shell_thickness = NumericUnitInput(
            value=getattr(self.section, "thickness", 1.0),
            unit=self.units.symbol("length") if self.units is not None else "",
            minimum=1e-12,
            maximum=1e12,
            decimals=6,
        )
        self.shell_points = QSpinBox()
        self.shell_points.setRange(1, 99)
        self.shell_points.setValue(getattr(self.section, "integration_points", 5))
        apply_primary_control_height(self.shell_points)

        integrated_layout.addWidget(field_block("Material", self.shell_material))
        integrated_layout.addWidget(
            field_row(
                field_block("Thickness", self.shell_thickness),
                field_block("Integration points", self.shell_points),
            )
        )
        integrated_layout.addStretch(1)
        self.shell_stack.addWidget(integrated)

        abd = QWidget()
        abd_layout = QVBoxLayout(abd)
        abd_layout.setContentsMargins(0, 0, 0, 0)
        abd_layout.setSpacing(12)

        abd_group = QGroupBox("6 × 6 generalized stiffness matrix")
        abd_box = QVBoxLayout(abd_group)
        self.abd = MatrixEditor(6, 6, getattr(self.section, "abd_matrix", None))
        abd_box.addWidget(self.abd)

        shear_group = QGroupBox("2 × 2 transverse shear matrix")
        shear_box = QVBoxLayout(shear_group)
        self.shear = MatrixEditor(2, 2, getattr(self.section, "shear_matrix", None))
        shear_box.addWidget(self.shear)

        abd_layout.addWidget(abd_group)
        abd_layout.addWidget(shear_group)
        abd_layout.addStretch(1)
        self.shell_stack.addWidget(abd)

        self.shell_definition.currentIndexChanged.connect(
            self.shell_stack.setCurrentIndex
        )
        self.shell_stack.setCurrentIndex(
            SHELL_TYPES.index(self.shell_definition.currentText())
        )
        return page

    def _beam_page(self, materials, profiles, material, profile, cm, cp):
        """Build the material/profile selectors for beam sections."""
        page, layout = self._vertical_page()
        mat = ReferenceSelector(materials, material, cm)
        prof = ReferenceSelector(profiles, profile, cp)
        layout.addWidget(
            field_row(
                field_block("Material", mat),
                field_block("Profile", prof),
            )
        )
        layout.addStretch(1)
        return page, mat, prof

    def _truss_page(self, materials, material, callback):
        """Build the material and cross-sectional-area editor for trusses."""
        page, layout = self._vertical_page()
        mat = ReferenceSelector(materials, material, callback)
        area = NumericUnitInput(
            value=getattr(self.section, "area", 1.0),
            unit=self.units.symbol("area") if self.units is not None else "",
            minimum=1e-12,
            maximum=1e30,
            decimals=6,
        )
        layout.addWidget(
            field_row(
                field_block("Material", mat),
                field_block("Cross-sectional area", area),
            )
        )
        layout.addStretch(1)
        return page, mat, area

    def _resize(self, *_args) -> None:
        """Refresh the preferred dialog size after switching section type."""
        self.adjustSize()

    def validate(self) -> bool:
        """Validate naming and required section references before committing."""
        name = self.name.text().strip()
        values = self.values()
        kind = values["section_type"]
        if not name:
            QMessageBox.warning(self, "Invalid section", "Enter a section name.")
            return False
        duplicate = name.casefold() in self.existing_names
        unchanged = self.section is not None and name.casefold() == self.section.name.casefold()
        if duplicate and not unchanged:
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A section named '{name}' already exists.",
            )
            return False
        if kind in {"Solid", "Beam", "Truss"} and not values.get("material_ref"):
            QMessageBox.warning(
                self,
                "Missing material",
                "Create or select a material first.",
            )
            return False
        if kind == "Beam" and not values.get("profile_ref"):
            QMessageBox.warning(
                self,
                "Missing profile",
                "Create or select a beam profile first.",
            )
            return False
        if (
            kind == "Shell"
            and values["shell_definition"] == SHELL_TYPES[0]
            and not values.get("material_ref")
        ):
            QMessageBox.warning(
                self,
                "Missing material",
                "Create or select a material first.",
            )
            return False
        return True

    @staticmethod
    def _ref(value, kind):
        """Create a persistent entity reference for a selected resource."""
        return EntityRef(str(value), kind) if value else None

    def values(self) -> dict:
        """Return constructor values for the currently selected section type."""
        kind = self.kind.currentText()
        result = {"name": self.name.text().strip(), "section_type": kind}
        if kind == "Solid":
            result["material_ref"] = self._ref(
                self.solid_material[1].currentValue(),
                "Material",
            )
        elif kind == "Beam":
            result.update(
                material_ref=self._ref(self.beam_material.currentValue(), "Material"),
                profile_ref=self._ref(self.beam_profile.currentValue(), "Profile"),
            )
        elif kind == "Truss":
            result.update(
                material_ref=self._ref(self.truss_material.currentValue(), "Material"),
                area=self.truss_area.value(),
            )
        else:
            result["shell_definition"] = self.shell_definition.currentText()
            result["material_ref"] = (
                self._ref(self.shell_material.currentValue(), "Material")
                if self.shell_definition.currentIndex() == 0
                else None
            )
            result["thickness"] = self.shell_thickness.value()
            result["integration_points"] = self.shell_points.value()
            result["abd_matrix"] = self.abd.values()
            result["shear_matrix"] = self.shear.values()
        return result

    def prepare_new(self, default_name, existing_names) -> None:
        """Reset name state when Apply keeps a create dialog open."""
        self.section = None
        self.existing_names = {name.casefold() for name in existing_names}
        self.name.setText(default_name)
