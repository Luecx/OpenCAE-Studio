from dataclasses import dataclass, field


@dataclass
class QueryResult:
    summary: list[tuple[str, object]] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    matrix: list[list[object]] = field(default_factory=list)
