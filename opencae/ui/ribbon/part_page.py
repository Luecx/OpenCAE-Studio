from opencae.ui.actions.ids import A
from .part_selector import PartSelector
from .ribbon_page import ResponsiveRibbonPage
from .specs import RibbonGroupSpec


class PartPage(ResponsiveRibbonPage):
    """Part ribbon with width-driven group collapsing."""

    def __init__(self, actions, store, parent=None):
        self._part_selector = PartSelector(store)
        specs = (
            RibbonGroupSpec(
                "GEOMETRY",
                (
                    A.NEW_PART,
                    A.DUPLICATE_PART,
                    A.IMPORT_GEOMETRY,
                    A.IMPORT_MESH,
                    A.PARTITION,
                    A.REBUILD_GEOMETRY,
                    A.SUPPRESS_FEATURE,
                ),
                icon_action_id=A.NEW_PART,
            ),
            RibbonGroupSpec("DISPLAY", (A.VISIBILITY,)),
            RibbonGroupSpec(
                "DATUM",
                (A.DATUM_POINT, A.DATUM_VECTOR, A.DATUM_PLANE),
            ),
            RibbonGroupSpec(
                "MESH",
                (
                    A.DEFAULT_SEED,
                    A.EDGE_SEED,
                    A.ELEMENT_CONTROLS,
                    A.MESH_SETTINGS,
                    A.GENERATE_MESH,
                    A.CLEAR_MESH,
                ),
                icon_action_id=A.GENERATE_MESH,
            ),
            RibbonGroupSpec(
                "REGIONS",
                (
                    A.NODE_SET,
                    A.ELEMENT_SET,
                    A.SURFACE,
                    A.PART_RP,
                    A.PART_CSYS,
                ),
                icon_action_id=A.NODE_SET,
            ),
            RibbonGroupSpec("PROPERTIES", (A.SECTION_ASSIGNMENT,)),
        )
        super().__init__(
            specs,
            actions,
            leading_widgets=(self._part_selector,),
            parent=parent,
        )
        self.part_selector = self._part_selector


def create(actions, store):
    return PartPage(actions, store)
