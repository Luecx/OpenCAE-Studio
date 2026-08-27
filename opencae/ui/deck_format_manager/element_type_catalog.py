"""Describe concrete element records for FEMaster, Abaqus and CalculiX."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeckElementType:
    """Describe one semantic element with native codes per deck dialect."""

    key: str
    label: str
    node_count: int
    codes: tuple[tuple[str, str], ...]

    @property
    def code(self) -> str:
        """Return the FEMaster code retained for compatibility with existing callers."""
        return self.code_for("FEMaster") or ""

    def code_for(self, format_name: str) -> str | None:
        """Return the native element code for ``format_name`` when supported."""
        return dict(self.codes).get(str(format_name))

    @property
    def supported_formats(self) -> tuple[str, ...]:
        """Return every dialect with a native element counterpart."""
        return tuple(name for name, _code in self.codes)


ELEMENT_TYPES: tuple[DeckElementType, ...] = (
    DeckElementType(
        "t3",
        "Linear Truss",
        2,
        (("FEMaster", "T3"), ("Abaqus", "T3D2"), ("CalculiX", "T3D2")),
    ),
    DeckElementType(
        "b33",
        "Bernoulli Beam",
        2,
        (("FEMaster", "B33"), ("Abaqus", "B33"), ("CalculiX", "B31")),
    ),
    DeckElementType(
        "s3",
        "Linear Triangular Shell",
        3,
        (("FEMaster", "S3"), ("Abaqus", "S3"), ("CalculiX", "S3")),
    ),
    DeckElementType(
        "s4",
        "Linear Quadrilateral Shell",
        4,
        (("FEMaster", "S4"), ("Abaqus", "S4"), ("CalculiX", "S4")),
    ),
    DeckElementType(
        "s6",
        "Quadratic Triangular Shell",
        6,
        (("FEMaster", "S6"), ("Abaqus", "STRI65"), ("CalculiX", "S6")),
    ),
    DeckElementType(
        "s8",
        "Quadratic Quadrilateral Shell",
        8,
        (("FEMaster", "S8"), ("Abaqus", "S8R"), ("CalculiX", "S8")),
    ),
    DeckElementType(
        "c3d4",
        "Linear Tetrahedron",
        4,
        (("FEMaster", "C3D4"), ("Abaqus", "C3D4"), ("CalculiX", "C3D4")),
    ),
    DeckElementType(
        "c3d5",
        "Linear Pyramid",
        5,
        (("FEMaster", "C3D5"), ("Abaqus", "C3D5")),
    ),
    DeckElementType(
        "c3d6",
        "Linear Wedge",
        6,
        (("FEMaster", "C3D6"), ("Abaqus", "C3D6"), ("CalculiX", "C3D6")),
    ),
    DeckElementType(
        "c3d8",
        "Linear Hexahedron",
        8,
        (("FEMaster", "C3D8"), ("Abaqus", "C3D8"), ("CalculiX", "C3D8")),
    ),
    DeckElementType(
        "c3d8r",
        "Linear Reduced-Integration Hexahedron",
        8,
        (("FEMaster", "C3D8R"), ("Abaqus", "C3D8R"), ("CalculiX", "C3D8R")),
    ),
    DeckElementType(
        "c3d10",
        "Quadratic Tetrahedron",
        10,
        (("FEMaster", "C3D10"), ("Abaqus", "C3D10"), ("CalculiX", "C3D10")),
    ),
    DeckElementType(
        "c3d15",
        "Quadratic Wedge",
        15,
        (("FEMaster", "C3D15"), ("Abaqus", "C3D15"), ("CalculiX", "C3D15")),
    ),
    DeckElementType(
        "c3d20",
        "Quadratic Hexahedron",
        20,
        (("FEMaster", "C3D20"), ("Abaqus", "C3D20"), ("CalculiX", "C3D20")),
    ),
    DeckElementType(
        "c3d20r",
        "Quadratic Reduced-Integration Hexahedron",
        20,
        (("FEMaster", "C3D20R"), ("Abaqus", "C3D20R"), ("CalculiX", "C3D20R")),
    ),
)


def element_tree_nodes() -> tuple[dict, ...]:
    """Return concrete element leaves with dialect-specific display labels."""
    result = []
    for element in ELEMENT_TYPES:
        labels = {
            format_name: f"{element.label} — {code}"
            for format_name, code in element.codes
        }
        result.append(
            {
                "key": f"mesh.elements.{element.key}",
                "label": labels.get("FEMaster", element.label),
                "format_labels": labels,
                "supported_formats": element.supported_formats,
            }
        )
    return tuple(result)


def element_template_specs() -> dict[str, dict]:
    """Return explicit loop templates using each dialect's native element code."""
    result: dict[str, dict] = {}
    for element in ELEMENT_TYPES:
        femaster = element.code_for("FEMaster")
        if femaster is None:
            continue
        spec = _spec(element, femaster)
        variants = {}
        for format_name in ("Abaqus", "CalculiX"):
            code = element.code_for(format_name)
            if code is not None:
                variants[format_name] = {"template": _template(code)}
        if variants:
            spec["formats"] = variants
        result[f"mesh.elements.{element.key}"] = spec
    return result


def _spec(element: DeckElementType, code: str) -> dict:
    """Build one element record specification for the canonical tree leaf."""
    return {
        "template": _template(code),
        "fields": (
            (
                "element_set",
                "Generated element-set name for this flattened block",
                "PART_E1",
            ),
        ),
        "loops": (
            {
                "collection": "elements",
                "item": "element",
                "description": "Elements written using the selected native element type.",
                "fields": (
                    ("id", "Solver element identifier", 42),
                    (
                        "connectivity",
                        f"Ordered {element.node_count}-node connectivity",
                        _connectivity_example(element.node_count, start=101),
                    ),
                ),
                "examples": (
                    {
                        "id": 42,
                        "connectivity": _connectivity_example(
                            element.node_count,
                            start=101,
                        ),
                    },
                    {
                        "id": 43,
                        "connectivity": _connectivity_example(
                            element.node_count,
                            start=201,
                        ),
                    },
                ),
            },
        ),
        "commands": ("ELEMENT",),
    }


def _template(code: str) -> str:
    """Return the common native ELEMENT block for one dialect-specific code."""
    return (
        f"*ELEMENT, TYPE={code}, ELSET={{element_set}}\n"
        "{for element in elements}\n"
        "{element.id}, {element.connectivity}\n"
        "{endfor}"
    )


def _connectivity_example(node_count: int, *, start: int) -> str:
    """Return a compact representative connectivity list."""
    return ", ".join(str(start + index) for index in range(node_count))
