from dataclasses import dataclass
from opencae.ui.foundation.icons import IconKind

@dataclass(frozen=True)
class ActionSpec:
    id: str
    text: str
    icon: IconKind
    handler: callable
    shortcut: str | None = None
    status_tip: str = ''
