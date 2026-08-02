from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DeckWriter:
    lines: list[str] = field(default_factory=list)

    def line(self, text: str = "") -> None:
        self.lines.append(text)

    def extend(self, lines: list[str] | tuple[str, ...]) -> None:
        self.lines.extend(lines)

    def comment(self, text: str, prefix: str = "**") -> None:
        self.line(f"{prefix} {text}")

    def text(self) -> str:
        return "\n".join(self.lines).rstrip() + "\n"
