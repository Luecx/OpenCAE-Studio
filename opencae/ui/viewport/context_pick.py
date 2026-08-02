class ContextPickManager:
    def __init__(self, owner):
        self.owner = owner
        self.active = False
        self.allowed = set()
        self.callback = None
        self.previous_mode = "auto"

    def begin(self, allowed, callback):
        self.cancel()
        self.active = True
        self.allowed = {str(value).lower() for value in allowed}
        self.callback = callback
        self.previous_mode = self.owner.selection_mode
        self.owner.set_selection_mode(self._mode())
        self.owner.message.emit("Pick " + ", ".join(sorted(self.allowed)))

    def consume(self, entities):
        if not self.active or not entities:
            return False
        entity = next((item for item in entities if self._accepted(item)), None)
        if entity is None:
            self.owner.message.emit("The selected entity is not valid for this field")
            return True
        callback = self.callback
        self.cancel()
        if callback:
            callback(entity)
        return True

    def cancel(self):
        if not self.active:
            return
        previous = self.previous_mode
        self.active = False; self.allowed.clear(); self.callback = None
        self.owner.set_selection_mode(previous)

    def _mode(self):
        if self.allowed <= {"point", "vertex", "node", "rp", "datum_point"}: return "point"
        basic = self.allowed & {"edge", "face", "cell", "element"}
        return next(iter(basic)) if len(basic) == 1 and len(self.allowed) == 1 else "auto"

    def _accepted(self, entity):
        kind = str(entity.get("kind") or entity.get("mesh_entity") or "").lower()
        return kind in self.allowed or ("point" in self.allowed and kind in {"vertex", "node", "rp", "datum_point"})
