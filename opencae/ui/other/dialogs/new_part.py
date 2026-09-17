from PyQt6.QtWidgets import QMessageBox

from opencae.ui.components.fields import FieldSpec
from opencae.ui.components.form_dialog import FormDialog


class NewPartDialog(FormDialog):
    """Create/edit Part metadata and choose the initial authored geometry flow."""

    def __init__(
        self,
        existing_names=(),
        part=None,
        parent=None,
        default_name="Part-1",
    ):
        self.existing_names = {name.casefold() for name in existing_names}
        self.part = part
        fields = [
            FieldSpec(
                "name",
                "Name",
                "text",
                getattr(part, "name", default_name),
            ),
            FieldSpec(
                "part_type",
                "Part type",
                "choice",
                getattr(part, "metadata", {}).get("part_type", "3D deformable"),
                ("3D deformable", "2D planar"),
            ),
        ]
        if part is None:
            fields.append(
                FieldSpec(
                    "geometry_mode",
                    "Initial geometry",
                    "choice",
                    "Empty",
                    ("Empty", "Planar sketch", "Extrusion", "Revolve"),
                )
            )
        super().__init__("Edit Part" if part else "New Part", tuple(fields), parent)

    def accept(self):
        values = self.values()
        name = values["name"]
        if not name:
            QMessageBox.warning(self, "Invalid part", "Enter a part name.")
            return
        if name.casefold() in self.existing_names and (
            self.part is None or name.casefold() != self.part.name.casefold()
        ):
            QMessageBox.warning(
                self,
                "Duplicate name",
                f"A part named '{name}' already exists.",
            )
            return
        if self.part is None:
            mode = values.get("geometry_mode", "Empty")
            part_type = values.get("part_type", "3D deformable")
            if part_type == "2D planar" and mode in {"Extrusion", "Revolve"}:
                QMessageBox.warning(
                    self,
                    "Incompatible geometry",
                    "Extrusion and Revolve create 3D geometry. Choose 'Planar sketch' "
                    "or change the Part type to '3D deformable'.",
                )
                return
        super().accept()
