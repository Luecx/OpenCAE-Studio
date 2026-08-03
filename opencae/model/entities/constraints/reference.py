from dataclasses import dataclass, field

from ...core import EntityRef, as_entity_ref, register_model_type
from .types import ConstraintReferenceKind


@register_model_type("constraint_reference")
@dataclass(frozen=True)
class ConstraintReference:
    kind: ConstraintReferenceKind | str = ConstraintReferenceKind.UNKNOWN
    ref: EntityRef = field(default_factory=EntityRef)
    instance_ref: EntityRef | None = None

    def __post_init__(self):
        object.__setattr__(self, "kind", ConstraintReferenceKind.coerce(self.kind))

    def bound_to(self, entity):
        return ConstraintReference(self.kind, self.ref.bound_to(entity), self.instance_ref)

    @property
    def key(self):
        instance_id = self.instance_ref.entity_id if self.instance_ref else ""
        return f"{instance_id}:{self.ref.entity_id or self.ref.legacy_name}"


def as_reference(value, kind=ConstraintReferenceKind.UNKNOWN):
    if isinstance(value, ConstraintReference):
        return value
    if isinstance(value, EntityRef):
        return ConstraintReference(kind, value)
    return ConstraintReference(kind, as_entity_ref(value, ConstraintReferenceKind.coerce(kind).value.replace(" ", "")))
