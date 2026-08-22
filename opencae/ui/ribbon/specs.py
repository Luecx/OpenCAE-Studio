from dataclasses import dataclass


@dataclass(frozen=True)
class RibbonMenuSpec:
    label: str
    primary_action_id: str
    action_ids: tuple[str, ...]


@dataclass(frozen=True)
class RibbonGroupSpec:
    title: str
    action_ids: tuple[str, ...]
    layout_items: tuple[str | RibbonMenuSpec, ...] = ()
