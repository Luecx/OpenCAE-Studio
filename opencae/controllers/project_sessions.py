"""Helpers for routing asynchronous work to the Project that owns an entity."""

from __future__ import annotations


class ProjectStoreView:
    """Pin ``project`` reads to one document while delegating store operations.

    The multi-project store itself remains the mutation boundary, so parent/entity
    ids still route writes to the correct session. This view only prevents a long-
    running worker from observing whichever project tab happens to be active.
    """

    def __init__(self, store, entity_id):
        self._store = store
        self._entity_id = str(entity_id)

    @property
    def project(self):
        resolver = getattr(self._store, "project_for_entity", None)
        if callable(resolver):
            project = resolver(self._entity_id)
            if project is not None:
                return project
        return self._store.project

    def __getattr__(self, name):
        return getattr(self._store, name)


def project_store_for_entity(store, entity_id):
    """Return a project-pinned view when multi-document routing is available."""
    if callable(getattr(store, "project_for_entity", None)):
        return ProjectStoreView(store, entity_id)
    return store


def run_for_entity(owner, entity_id, callback, *args, **kwargs):
    """Run a callback with ``owner.store.project`` pinned to the owning document.

    The global MultiProjectStore never changes its visible project during this
    callback. Mutations delegate back into it and are routed by entity/parent id,
    while UI slots continue to observe the user's currently selected tab.
    """
    store = getattr(owner, "store", None)
    if store is None or not callable(getattr(store, "project_for_entity", None)):
        return callback(*args, **kwargs)
    owner.store = ProjectStoreView(store, entity_id)
    try:
        return callback(*args, **kwargs)
    finally:
        owner.store = store
        refresh = getattr(getattr(owner, "parent", None), "refresh_action_states", None)
        if callable(refresh):
            refresh()
