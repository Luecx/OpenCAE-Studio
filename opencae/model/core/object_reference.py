"""Defines the descriptor exposing persisted EntityRef fields as objects."""

from __future__ import annotations


class EntityObjectReference:
    """Public object view over one persisted ``*_ref`` entity relationship."""

    def __init__(self, ref_name: str, expected_type: str):
        """Bind the descriptor to its storage field and expected model type."""
        self.ref_name = ref_name
        self.expected_type = expected_type
        self.cache_name = f"_resolved_{ref_name}"

    def __get__(self, instance, owner=None):
        """Resolve the stored EntityRef against the entity's current Project."""
        if instance is None:
            return self

        ref = getattr(instance, self.ref_name, None)
        if ref is None or not getattr(ref, "is_bound", False):
            instance.__dict__.pop(self.cache_name, None)
            return None

        cached = instance.__dict__.get(self.cache_name)
        if cached is not None and getattr(cached, "id", None) == ref.entity_id:
            return cached

        project = getattr(instance, "project", None)
        if project is None:
            return None
        resolved = project.try_resolve(ref)
        if resolved is not None:
            # Caching avoids repeatedly walking the ProjectIndex from property
            # rendering. Entity._bind_project clears this cache on graph rebinding.
            instance.__dict__[self.cache_name] = resolved
        return resolved

    def __set__(self, instance, value) -> None:
        """Persist an object relationship as a stable EntityRef."""
        from .entity import Entity
        from .reference import EntityRef

        if value is None:
            setattr(instance, self.ref_name, None)
            instance.__dict__.pop(self.cache_name, None)
            return
        if not isinstance(value, Entity):
            public_name = self.ref_name.removesuffix("_ref")
            raise TypeError(
                f"{type(instance).__name__}.{public_name} expects an Entity "
                f"object, not {type(value).__name__}"
            )

        current = getattr(instance, self.ref_name, None)
        expected = getattr(current, "expected_type", "") or self.expected_type
        setattr(instance, self.ref_name, EntityRef.of(value, expected))
        instance.__dict__[self.cache_name] = value
