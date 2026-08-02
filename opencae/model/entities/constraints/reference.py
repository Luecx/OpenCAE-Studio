from dataclasses import dataclass, field

from ...core import EntityRef, as_entity_ref, register_model_type
from .types import ConstraintReferenceKind


@register_model_type("constraint_reference")
@dataclass(frozen=True)
class ConstraintReference:
    kind: ConstraintReferenceKind | str = ConstraintReferenceKind.UNKNOWN
    ref: EntityRef = field(default_factory=EntityRef)

    def __post_init__(self):
        object.__setattr__(self, "kind", ConstraintReferenceKind.coerce(self.kind))

    def bound_to(self, entity):
        return ConstraintReference(self.kind, self.ref.bound_to(entity))


def as_reference(value, kind=ConstraintReferenceKind.UNKNOWN):
    if isinstance(value, ConstraintReference):
        return value
    if isinstance(value, EntityRef):
        return ConstraintReference(kind, value)
    return ConstraintReference(kind, as_entity_ref(value, ConstraintReferenceKind.coerce(kind).value.replace(" ", "")))
