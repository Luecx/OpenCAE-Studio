from dataclasses import dataclass, field

from ...core import register_model_type
from ..elements.base import ElementDefinition
from .control import MeshControl
from .element_block import ElementBlock
from .element_control import ElementControl
from .mesh_settings import MeshSettings
from .node_table import NodeTable
from .seed import Seed


@register_model_type("mesh_state")
@dataclass
class MeshState:
    settings: MeshSettings = field(default_factory=MeshSettings)
    seeds: list[Seed] = field(default_factory=list)
    controls: list[MeshControl] = field(default_factory=list)
    element_controls: list[ElementControl] = field(default_factory=list)
    elements: list[ElementDefinition] = field(default_factory=list)
    nodes: NodeTable = field(default_factory=NodeTable)
    element_blocks: list[ElementBlock] = field(default_factory=list)
    entity_nodes: dict[str, list[int]] = field(default_factory=dict)
    entity_elements: dict[str, list[int]] = field(default_factory=dict)
    node_count: int = 0
    element_count: int = 0
    mesh_dimension: int = 0
    minimum_quality: float | None = None
    mean_quality: float | None = None
    status: str = "Not generated"
