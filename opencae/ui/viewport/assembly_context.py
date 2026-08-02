from dataclasses import dataclass


@dataclass(frozen=True)
class ActorReference:
    instance_name: str | None
    dimension: int
    tag: int

    @property
    def label(self):
        names = {0: "Vertex", 1: "Edge", 2: "Face", 3: "Cell"}
        value = f"{names[self.dimension]}-{self.tag}"
        return f"{self.instance_name}.{value}" if self.instance_name else value
