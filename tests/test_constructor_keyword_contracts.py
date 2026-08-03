from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / "opencae"


def test_direct_project_constructor_keywords_match_signatures():
    """Catch stale keyword arguments after internal widget/model API refactors.

    Only unambiguous direct calls such as ``WidgetName(..., keyword=value)`` are
    checked. Attribute calls and duplicated class names are intentionally ignored
    to avoid guessing runtime types.
    """

    sources = sorted(SOURCE_ROOT.rglob("*.py"))
    definitions: dict[str, list[tuple[Path, set[str], bool]]] = defaultdict(list)

    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            constructor = next(
                (
                    item
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__"
                ),
                None,
            )
            if constructor is None:
                continue
            arguments = constructor.args
            accepted = {
                argument.arg
                for argument in (*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs)
                if argument.arg != "self"
            }
            definitions[node.name].append((path, accepted, arguments.kwarg is not None))

    failures: list[str] = []
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            candidates = definitions.get(node.func.id, ())
            if len(candidates) != 1:
                continue
            definition_path, accepted, has_var_keywords = candidates[0]
            if has_var_keywords:
                continue
            for keyword in node.keywords:
                if keyword.arg is not None and keyword.arg not in accepted:
                    failures.append(
                        f"{path.relative_to(ROOT)}:{node.lineno}: {node.func.id}() passes unsupported "
                        f"keyword {keyword.arg!r}; definition: {definition_path.relative_to(ROOT)}"
                    )

    assert not failures, "\n" + "\n".join(failures)
