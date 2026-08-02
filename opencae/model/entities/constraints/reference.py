from dataclasses import dataclass

from ...core import register_model_type
from .types import ConstraintReferenceKind


@register_model_type("constraint_reference")
@dataclass(frozen=True)
class ConstraintReference:
    name: str = ""
    kind: ConstraintReferenceKind | str = ConstraintReferenceKind.UNKNOWN

    def __post_init__(self):
        object.__setattr__(self, "kind", ConstraintReferenceKind.coerce(self.kind))


def as_reference(value, kind=ConstraintReferenceKind.UNKNOWN):
    if isinstance(value, ConstraintReference): return value
    return ConstraintReference(str(value or ""), kind)
