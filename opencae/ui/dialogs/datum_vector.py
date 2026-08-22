import numpy as np

from opencae.ui.core.widgets import XYZPicker

from .datum_base import DatumDialogBase
from .datum_forms import check, choice, csys_choice, number, page, references


_POINT_KINDS = ("geometry_vertex", "datum_point", "reference_point")
_DIRECTION_KINDS = ("geometry_edge", "geometry_face", "datum_vector", "datum_plane")


class DatumVectorDialog(DatumDialogBase):
    METHODS = (
        "Components",
        "Between Two Points",
        "Along Edge",
        "Face Normal",
        "Coordinate-System Axis",
    )

    def __init__(self, default_name, existing_names=(), coordinate_systems=(), parent=None):
        super().__init__(
            "Create Datum Vector",
            self.METHODS,
            default_name,
            existing_names,
            parent,
        )

        self.origin = XYZPicker(allowed=_POINT_KINDS, value_kind="point")
        self.direction = XYZPicker(
            (1.0, 0.0, 0.0),
            allowed=_DIRECTION_KINDS,
            value_kind="direction",
        )
        self.add_page(
            page(
                (
                    ("Origin", self.origin),
                    ("Direction", self.direction),
                )
            )
        )

        self.point_1 = references("point")
        self.point_2 = references("point")
        self.add_page(
            page((("Start point", self.point_1), ("End point", self.point_2)))
        )

        self.edge = references("edge")
        self.position = number(.5, 0, 1)
        self.edge_flip = check("Reverse direction")
        self.add_page(
            page(
                (
                    ("Edge", self.edge),
                    ("Position", self.position),
                    ("", self.edge_flip),
                )
            )
        )

        self.face = references("face")
        self.face_flip = check("Reverse normal")
        self.add_page(page((("Face", self.face), ("", self.face_flip))))

        self.csys = csys_choice(coordinate_systems)
        self.axis = choice(("X / r", "Y / θ", "Z"))
        self.add_page(
            page((("Coordinate system", self.csys), ("Axis", self.axis)))
        )

    def values(self):
        method = self.method.currentText()
        if method == "Components":
            ox, oy, oz = self.origin.value()
            dx, dy, dz = self.direction.value()
            parameters = {
                "origin_x": ox,
                "origin_y": oy,
                "origin_z": oz,
                "direction_x": dx,
                "direction_y": dy,
                "direction_z": dz,
            }
        elif method == "Between Two Points":
            parameters = {
                "point_1": self.point_1.reference(),
                "point_2": self.point_2.reference(),
            }
        elif method == "Along Edge":
            parameters = {
                "edge": self.edge.reference(),
                "position": self.position.value(),
                "flip": self.edge_flip.isChecked(),
            }
        elif method == "Face Normal":
            parameters = {
                "face": self.face.reference(),
                "flip": self.face_flip.isChecked(),
            }
        else:
            parameters = _axis_parameters(
                self.csys.currentData(),
                self.axis.currentIndex(),
            )
        return {
            "name": self.name.text().strip(),
            "kind": "Vector",
            "method": method,
            "parameters": parameters,
        }


def _axis_parameters(system, index):
    x = np.asarray(system["axis_1"], float)
    x /= np.linalg.norm(x)
    y0 = np.asarray(system["axis_2"], float)
    y = y0 - np.dot(y0, x) * x
    y /= np.linalg.norm(y)
    z = np.cross(x, y)
    return {
        "origin_x": system["origin"][0],
        "origin_y": system["origin"][1],
        "origin_z": system["origin"][2],
        "axis": tuple((x, y, z)[index]),
    }
