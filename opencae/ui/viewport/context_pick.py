from __future__ import annotations

from opencae.model.selection import SelectableKind, SelectionMultiplicity, SelectionPolicy, ViewportHit


class ContextPickManager:
    """Own exactly one viewport pick session.

    A session reports when it finishes, whether it ended because a single item
    was accepted, the user clicked Finish Picking, the dialog closed, or a
    different region field started picking.  This keeps all pick buttons in
    sync with the one global viewport picker.
    """

    def __init__(self, owner):
        self.owner = owner
        self.active = False
        self.policy: SelectionPolicy | None = None
        self.callback = None
        self.finished_callback = None
        self.previous_mode = "auto"

    @property
    def allowed(self):
        return set(self.policy.accepted_kinds) if self.policy else set()

    def begin(self, policy, callback, multiple=None, finished=None):
        # Starting another field is an explicit hand-off.  The old field is
        # notified first so its button cannot remain checked.
        self.cancel()
        if not isinstance(policy, SelectionPolicy):
            policy = SelectionPolicy.create(policy, multiple=bool(multiple))
        self.active = True
        self.policy = policy
        self.callback = callback
        self.finished_callback = finished
        self.previous_mode = self.owner.selection_mode
        self.owner.set_selection_mode(self._mode())
        names = ", ".join(sorted(value.value.replace("_", " ") for value in policy.accepted_kinds))
        suffix = " (Shift adds, Ctrl removes, Finish Picking ends)" if policy.multiplicity == SelectionMultiplicity.MULTIPLE else ""
        self.owner.message.emit(f"Pick {names}{suffix}")

    def consume(self, entities):
        if not self.active or not entities:
            return False
        hits = tuple(entities)
        if any(not isinstance(value, ViewportHit) for value in hits):
            raise TypeError("Context picking requires typed ViewportHit values")
        accepted = [value for value in hits if self._accepted(value)]
        if not accepted:
            self.owner.message.emit("The picked viewport entity is not valid for this region")
            return True
        callback = self.callback
        if self.policy.multiplicity == SelectionMultiplicity.SINGLE:
            value = accepted[-1]
            # End the session before applying the hit.  The persistent dialog
            # preview is then drawn after the temporary picker highlight has
            # been cleared by restoring the previous selection mode.
            self.cancel()
            if callback:
                callback(value)
        elif callback:
            for value in accepted:
                callback(value)
        return True

    def cancel(self):
        if not self.active:
            return
        previous = self.previous_mode
        finished = self.finished_callback
        # Clear state before restoring the picker.  Restoring calls back into
        # picker configuration and must observe an inactive context session.
        self.active = False
        self.policy = None
        self.callback = None
        self.finished_callback = None
        self.owner.set_selection_mode(previous)
        if finished:
            finished()

    def accepts(self, kind) -> bool:
        return bool(self.policy and SelectableKind.coerce(kind) in self.policy.accepted_kinds)

    def refresh_for_display(self):
        """Re-select the appropriate picker when Geometry/Mesh display changes."""
        if self.active:
            self.owner.set_selection_mode(self._mode())

    def _mode(self):
        kinds = self.policy.accepted_kinds
        previous = self.previous_mode
        if self.owner.display_mode == "mesh":
            points_allowed = bool(kinds & {SelectableKind.MESH_NODE, SelectableKind.REFERENCE_POINT})
            elements_allowed = bool(kinds & {SelectableKind.MESH_ELEMENT, SelectableKind.MESH_FACET})
            if previous == "element" and elements_allowed:
                return "element"
            if previous == "point" and points_allowed:
                return "point"
            if points_allowed and not elements_allowed:
                return "point"
            if elements_allowed and not points_allowed:
                return "element"
            return "point" if points_allowed else "element"
        point_kinds = {SelectableKind.GEOMETRY_VERTEX, SelectableKind.MESH_NODE, SelectableKind.REFERENCE_POINT}
        if kinds <= point_kinds:
            return "point"
        geometry = {
            SelectableKind.GEOMETRY_VERTEX: "point",
            SelectableKind.GEOMETRY_EDGE: "edge",
            SelectableKind.GEOMETRY_FACE: "face",
            SelectableKind.GEOMETRY_CELL: "cell",
        }
        active = {geometry[value] for value in kinds if value in geometry}
        if previous in active:
            return previous
        return next(iter(active)) if len(active) == 1 else "auto"

    def _accepted(self, hit):
        return hit.kind in self.policy.accepted_kinds
