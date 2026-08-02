from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    name: str
    keywords: frozenset[str] = frozenset()
    required: frozenset[str] = frozenset()
    variants: tuple[str, ...] = ()
    scope: str = "ROOT"
