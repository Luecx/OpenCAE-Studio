from opencae.ui.core.widgets import XYZPicker

from .datum_base import DatumDialogBase
from .datum_forms import choice, csys_choice, number, page, references


_POINT_KINDS = ("geometry_vertex", "datum_point", "reference_point")


class DatumPointDialog(DatumDialogBase):
    METHODS = ("Coordinates", "Between Two Points", "Along Edge")

    def __init__(self, default_name, existing_names=(), coordinate_systems=(), parent=None, units=None):
        super().__init__(
            "Create Datum Point",
            self.METHODS,
            default_name,
            existing_names,
            parent,
        )
        self.units = units
        length_suffix = units.suffix("length") if units is not None else ""

        self.coordinate = XYZPicker(
            allowed=_POINT_KINDS,
            value_kind="point",
            suffix=length_suffix,
        )
        self.csys = csys_choice(coordinate_systems)
        self.add_page(
            page(
                (
                    ("Coordinate system", self.csys),
                    ("Position", self.coordinate),
                )
            )
        )

        self.point_1 = references("point")
        self.point_2 = references("point")
        self.ratio = number(.5, 0, 1)
        self.add_page(
            page(
                (
                    ("Point 1", self.point_1),
                    ("Point 2", self.point_2),
                    ("Ratio", self.ratio),
                )
            )
        )

        self.edge = references("edge")
        self.definition = choice(
            ("Normalized parameter", "Arc length from start", "Arc length from end")
        )
        self.position = number(.5, 0, 1e15)
        self.definition.currentTextChanged.connect(self._sync_position_unit)
        self._sync_position_unit(self.definition.currentText())
        self.add_page(
            page(
                (
                    ("Edge", self.edge),
                    ("Definition", self.definition),
                    ("Position", self.position),
                )
            )
        )

    def _sync_position_unit(self, definition):
        suffix = ""
        if str(definition) != "Normalized parameter" and self.units is not None:
            suffix = self.units.suffix("length")
        self.position.setSuffix(suffix)

    def values(self):
        method = self.method.currentText()
        parameters = {}
        if method == "Coordinates":
            x, y, z = self.coordinate.value()
            parameters = {
                "coordinate_x": x,
                "coordinate_y": y,
                "coordinate_z": z,
                "coordinate_system": self.csys.currentData(),
            }
        elif method == "Between Two Points":
            parameters = {
                "point_1": self.point_1.reference(),
                "point_2": self.point_2.reference(),
                "ratio": self.ratio.value(),
            }
        else:
            parameters = {
                "edge": self.edge.reference(),
                "definition": self.definition.currentText(),
                "position": self.position.value(),
            }
        return {
            "name": self.name.text().strip(),
            "kind": "Point",
            "method": method,
            "parameters": parameters,
        }
