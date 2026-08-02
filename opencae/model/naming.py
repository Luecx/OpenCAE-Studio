from __future__ import annotations

from collections.abc import Iterable


def normalized(name: str) -> str:
    return str(name).strip().casefold()


def names_of(collection: Iterable) -> tuple[str, ...]:
    return tuple(str(getattr(item, "name", item)).strip() for item in collection)


def name_exists(collection: Iterable, name: str, exclude_id: str | None = None, exclude_name: str = "") -> bool:
    folded = normalized(name); excluded = normalized(exclude_name)
    return any(
        normalized(getattr(item, "name", item)) == folded
        and getattr(item, "id", None) != exclude_id
        and normalized(getattr(item, "name", item)) != excluded
        for item in collection
    )


def next_name(prefix: str, collection: Iterable) -> str:
    return next_name_from_names(prefix, names_of(collection))


def next_name_from_names(prefix: str, names: Iterable[str]) -> str:
    used = {normalized(name) for name in names}; index = 1
    while normalized(f"{prefix}-{index}") in used:
        index += 1
    return f"{prefix}-{index}"


def is_unique(name: str, names: Iterable[str], current_name: str = "") -> bool:
    folded = normalized(name)
    if not folded:
        return False
    current = normalized(current_name)
    return folded == current or folded not in {normalized(value) for value in names}
