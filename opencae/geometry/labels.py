from __future__ import annotations

_DIM_PREFIX = {0: "Vertex", 1: "Edge", 2: "Face", 3: "Cell"}
_PREFIX_DIM = {value.lower(): key for key, value in _DIM_PREFIX.items()}


def entity_label(dim: int, tag: int) -> str:
    return f"{_DIM_PREFIX.get(dim, 'Entity')}-{tag}"


def parse_entity_label(value: str) -> tuple[int, int] | None:
    text = value.strip()
    if "-" not in text:
        return None
    prefix, number = text.rsplit("-", 1)
    dim = _PREFIX_DIM.get(prefix.lower())
    if dim is None or not number.isdigit():
        return None
    return dim, int(number)


def parse_labels(values: list[str], expected_dim: int | None = None) -> list[tuple[int, int]]:
    result = []
    for value in values:
        parsed = parse_entity_label(value)
        if parsed and (expected_dim is None or parsed[0] == expected_dim):
            result.append(parsed)
    return result
