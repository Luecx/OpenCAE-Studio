from __future__ import annotations

from opencae.model.selection import (
    SelectableKind,
    SelectionMultiplicity,
    SelectionPolicy,
    ViewportHit,
)


class ContextPickManager:
    """Own exactly one explicit viewport pick session.

    Outside such a session the viewport picker is dormant. A dialog starts a
    session through its mouse button, and ending or handing off that session
    disables viewport selection again.
    """

    def __init__(self, owner):
        self.owner = owner
        self.active = False
        self.policy: SelectionPolicy | None = None
        self.callback = None
        self.finished_callback = None
        self.previous_mode = "none"

    @property
    def allowed(self):
        return set(self.policy.accepted_kinds) if self.policy else set()

    def begin(self, policy, callback, multiple=None, finished=None):
        # Starting another field is an explicit hand-off. The old field is
        # notified first so its button cannot remain checked.
        self.cancel()
        if not isinstance(policy, SelectionPolicy):
            policy = SelectionPolicy.create(policy, multiple=bool(multiple))

        self.active = True
        self.policy = policy
        self.callback = callback
        self.finished_callback = finished
        self.previous_mode = self.owner.selection_mode

        self._sync_toolbar()
        self.owner.set_selection_mode(self._mode())

        names = ", ".join(
            sorted(value.value.replace("_", " ") for value in policy.accepted_kinds)
        )
        suffix = (
            " (Shift adds, Ctrl removes)"
            if policy.multiplicity == SelectionMultiplicity.MULTIPLE
            else ""
        )
        self.owner.message.emit(f"Pick {names}{suffix}")

    def consume(self, entities):
        if not self.active or not entities:
            return False
        hits = tuple(entities)
        if any(not isinstance(value, ViewportHit) for value in hits):
            raise TypeError("Context picking requires typed ViewportHit values")
        accepted = [value for value in hits if self._accepted(value)]
        if not accepted:
            self.owner.message.emit(
                "The picked viewport entity is not valid for this region"
            )
            return True

        callback = self.callback
        if self.policy.multiplicity == SelectionMultiplicity.SINGLE:
            value = accepted[-1]
            # End the session before applying the hit. The persistent dialog
            # preview is then drawn after the temporary picker state is reset.
            self.cancel()
            if callback:
                callback(value)
        elif callback:
            for value in accepted:
                callback(value)
        return True

    def cancel(self):
        if not self.active:
            # Keep dormant state deterministic even if a closing dialog calls
            # cancel more than once.
            self.owner.toolbar.set_selection_enabled(False)
            if self.owner.selection_mode != "none":
                self.owner.set_selection_mode("none")
            return

        finished = self.finished_callback
        self.active = False
        self.policy = None
        self.callback = None
        self.finished_callback = None

        self.owner.set_selection_mode("none")
        self.owner.toolbar.set_selection_enabled(False)
        if finished:
            finished()

    def accepts(self, kind) -> bool:
        return bool(
            self.policy
            and SelectableKind.coerce(kind) in self.policy.accepted_kinds
        )

    def refresh_for_display(self):
        """Reconfigure the explicit picker after Geometry/Mesh display changes."""
        if self.active:
            self._sync_toolbar()
            self.owner.set_selection_mode(self._mode())

    def _sync_toolbar(self):
        self.owner.toolbar.set_selection_enabled(True, self._allowed_modes())

    def _allowed_modes(self):
        kinds = self.policy.accepted_kinds if self.policy else frozenset()
        modes = []
        if self.owner.display_mode == "mesh":
            if kinds & {
                SelectableKind.MESH_NODE,
                SelectableKind.REFERENCE_POINT,
                SelectableKind.DATUM_POINT,
            }:
                modes.append("point")
            if kinds & {SelectableKind.MESH_ELEMENT, SelectableKind.MESH_FACET}:
                modes.append("element")
            if kinds & {SelectableKind.DATUM_VECTOR, SelectableKind.DATUM_PLANE}:
                return ("auto",)
        else:
            if kinds & {
                SelectableKind.GEOMETRY_VERTEX,
                SelectableKind.REFERENCE_POINT,
                SelectableKind.DATUM_POINT,
            }:
                modes.append("point")
            if SelectableKind.GEOMETRY_EDGE in kinds:
                modes.append("edge")
            if SelectableKind.GEOMETRY_FACE in kinds:
                modes.append("face")
            if SelectableKind.GEOMETRY_CELL in kinds:
                modes.append("cell")

            # Datum vectors and planes are standalone actors rather than one of
            # the geometry entity modes.  Auto uses the hardware actor picker
            # and can therefore discriminate them together with edges/faces.
            if kinds & {SelectableKind.DATUM_VECTOR, SelectableKind.DATUM_PLANE}:
                return ("auto",)
        if len(modes) > 1:
            modes.insert(0, "auto")
        return tuple(modes)

    def _mode(self):
        allowed = self._allowed_modes()
        previous = self.previous_mode
        if previous in allowed:
            return previous
        if len(allowed) == 1:
            return allowed[0]
        if "auto" in allowed:
            return "auto"
        return allowed[0] if allowed else "none"

    def _accepted(self, hit):
        return hit.kind in self.policy.accepted_kinds
