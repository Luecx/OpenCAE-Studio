from PyQt6.QtWidgets import QHBoxLayout, QWidget

from opencae.ui.actions.ids import A
from .part_selector import PartSelector
from .ribbon_group import RibbonGroup
from .specs import RibbonGroupSpec


def create(actions, store):
    page = QWidget(); layout = QHBoxLayout(page); layout.setContentsMargins(5, 0, 0, 0); layout.setSpacing(0)
    page.part_selector = PartSelector(store); layout.addWidget(page.part_selector)
    specs = (
        RibbonGroupSpec("GEOMETRY", (A.NEW_PART, A.DUPLICATE_PART, A.IMPORT_GEOMETRY, A.IMPORT_MESH, A.PARTITION, A.REBUILD_GEOMETRY, A.SUPPRESS_FEATURE)),
        RibbonGroupSpec("DATUM", (A.DATUM_POINT, A.DATUM_VECTOR, A.DATUM_PLANE)),
        RibbonGroupSpec("MESH", (A.DEFAULT_SEED, A.EDGE_SEED, A.ELEMENT_CONTROLS, A.MESH_SETTINGS, A.GENERATE_MESH, A.CLEAR_MESH)),
        RibbonGroupSpec("REGIONS", (A.NODE_SET, A.ELEMENT_SET, A.SURFACE, A.PART_RP, A.PART_CSYS)),
        RibbonGroupSpec("PROPERTIES", (A.SECTION_ASSIGNMENT,)),
    )
    for spec in specs: layout.addWidget(RibbonGroup(spec, actions))
    layout.addStretch(1); return page
