from dataclasses import dataclass


@dataclass(frozen=True)
class RibbonGroupSpec:
    title: str
    action_ids: tuple[str, ...]
    layout_items: tuple[str | tuple[str, ...], ...] = ()
