from dataclasses import dataclass


@dataclass(frozen=True)
class ActorReference:
    instance_id: str | None
    dimension: int
    tag: int
    instance_label: str = ""

    @property
    def label(self):
        names = {0: "Vertex", 1: "Edge", 2: "Face", 3: "Cell"}
        value = f"{names[self.dimension]}-{self.tag}"
        return f"{self.instance_label}.{value}" if self.instance_label else value
