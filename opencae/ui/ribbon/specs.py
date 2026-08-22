from dataclasses import dataclass


@dataclass(frozen=True)
class RibbonGroupSpec:
    title: str
    action_ids: tuple[str, ...]
    collapsed: bool = False
    icon_action_id: str | None = None
