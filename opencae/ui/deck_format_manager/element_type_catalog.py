"""Describe concrete deck element records exposed by the format editor."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeckElementType:
    """Describe one concrete element keyword/type handled by a deck profile."""

    key: str
    label: str
    code: str
    node_count: int


ELEMENT_TYPES: tuple[DeckElementType, ...] = (
    DeckElementType("t3", "Linear Truss — T3", "T3", 2),
    DeckElementType("b33", "Bernoulli Beam — B33", "B33", 2),
    DeckElementType("s3", "Linear Triangular Shell — S3", "S3", 3),
    DeckElementType(
        "mitc3frt",
        "Linear Triangular Finite-Rotation Shell — MITC3FRT",
        "MITC3FRT",
        3,
    ),
    DeckElementType("s6", "Quadratic Triangular Shell — S6", "S6", 6),
    DeckElementType(
        "mitc6frt",
        "Quadratic Triangular Finite-Rotation Shell — MITC6FRT",
        "MITC6FRT",
        6,
    ),
    DeckElementType("s4", "Linear Quadrilateral Shell — S4", "S4", 4),
    DeckElementType("mitc4", "Linear MITC Quadrilateral Shell — MITC4", "MITC4", 4),
    DeckElementType(
        "mitc4frt",
        "Linear Finite-Rotation MITC Quadrilateral Shell — MITC4FRT",
        "MITC4FRT",
        4,
    ),
    DeckElementType("s8", "Quadratic Quadrilateral Shell — S8", "S8", 8),
    DeckElementType("mitc8", "Quadratic MITC Quadrilateral Shell — MITC8", "MITC8", 8),
    DeckElementType(
        "mitc8frt",
        "Quadratic Finite-Rotation MITC Quadrilateral Shell — MITC8FRT",
        "MITC8FRT",
        8,
    ),
    DeckElementType("qspt", "QSPT Shell — QSPT", "QSPT", 4),
    DeckElementType("c3d4", "Linear Tetrahedron — C3D4", "C3D4", 4),
    DeckElementType("c3d10", "Quadratic Tetrahedron — C3D10", "C3D10", 10),
    DeckElementType("c3d5", "Linear Pyramid — C3D5", "C3D5", 5),
    DeckElementType("c3d13", "Quadratic Pyramid — C3D13", "C3D13", 13),
    DeckElementType("c3d6", "Linear Wedge — C3D6", "C3D6", 6),
    DeckElementType("c3d15", "Quadratic Wedge — C3D15", "C3D15", 15),
    DeckElementType("c3d8", "Linear Hexahedron — C3D8", "C3D8", 8),
    DeckElementType(
        "c3d8r",
        "Linear Reduced-Integration Hexahedron — C3D8R",
        "C3D8R",
        8,
    ),
    DeckElementType("c3d20", "Quadratic Hexahedron — C3D20", "C3D20", 20),
    DeckElementType(
        "c3d20r",
        "Quadratic Reduced-Integration Hexahedron — C3D20R",
        "C3D20R",
        20,
    ),
)


def element_tree_nodes() -> tuple[dict, ...]:
    """Return concrete element leaves in their default deck ordering."""
    return tuple(
        {
            "key": f"mesh.elements.{element.key}",
            "label": element.label,
        }
        for element in ELEMENT_TYPES
    )


def element_template_specs() -> dict[str, dict]:
    """Return one explicit loop-based template spec per concrete element type."""
    return {
        f"mesh.elements.{element.key}": {
            "template": (
                f"*ELEMENT, TYPE={element.code}\n"
                "{for element in elements}\n"
                "{element.id}, {element.connectivity}\n"
                "{endfor}"
            ),
            "fields": (),
            "loops": (
                {
                    "collection": "elements",
                    "item": "element",
                    "description": f"Elements written as {element.code}.",
                    "fields": (
                        ("id", "Solver element identifier", "42"),
                        (
                            "connectivity",
                            f"Ordered {element.node_count}-node connectivity",
                            _connectivity_example(element.node_count, start=101),
                        ),
                    ),
                    "examples": (
                        {
                            "id": "42",
                            "connectivity": _connectivity_example(
                                element.node_count,
                                start=101,
                            ),
                        },
                        {
                            "id": "43",
                            "connectivity": _connectivity_example(
                                element.node_count,
                                start=201,
                            ),
                        },
                    ),
                },
            ),
        }
        for element in ELEMENT_TYPES
    }


def _connectivity_example(node_count: int, *, start: int) -> str:
    """Return a compact representative connectivity list."""
    return ", ".join(str(start + index) for index in range(node_count))
