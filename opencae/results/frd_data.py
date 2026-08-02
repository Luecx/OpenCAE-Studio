from dataclasses import dataclass, field
import numpy as np

@dataclass
class FrdFieldData:
    name: str
    components: list[str] = field(default_factory=list)
    values: dict[int, list[float]] = field(default_factory=dict)
    step_id: int = 1
    frame_id: int = 1
    frame_value: float = 0.0
    block_index: int = 0

@dataclass
class FrdData:
    nodes: dict[int, tuple[float, float, float]] = field(default_factory=dict)
    elements: list[tuple[int, int, list[int]]] = field(default_factory=list)
    fields: list[FrdFieldData] = field(default_factory=list)
    def node_order(self): return sorted(self.nodes)
    def points(self): return np.asarray([self.nodes[tag] for tag in self.node_order()],dtype=float)
    def steps(self): return list(dict.fromkeys(field.step_id for field in self.fields))
    def frames(self,step_id):
        return list(dict.fromkeys((field.frame_id,field.frame_value) for field in self.fields if field.step_id==step_id))
