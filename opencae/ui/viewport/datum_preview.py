from types import SimpleNamespace
from opencae.model.datums import create_datum
from .datum_overlay import DatumOverlay


class DatumPreview:
    def __init__(self): self.overlay = DatumOverlay()
    def clear(self, plotter): self.overlay.clear(plotter)
    def show(self, plotter, scene, values):
        self.clear(plotter)
        try: datum = create_datum(values["kind"], values.get("name") or "Preview", values["method"], values["parameters"])
        except (KeyError, TypeError, ValueError): return
        preview_scene = SimpleNamespace(datum_actors={}, assembly_instances={})
        self.overlay.show_part(plotter, SimpleNamespace(datums=[datum]), preview_scene)
        # A preview must never intercept a click intended for the source
        # vertex/edge/face or an existing datum reference underneath it.
        for actor in preview_scene.datum_actors:
            actor.SetPickable(False)
        plotter.render()
