from __future__ import annotations

from .catalog import ALL_COMMANDS
from .element_types import ELEMENT_TYPES


class FEMasterSyntaxError(ValueError):
    pass


_TYPE_COMMANDS = {
    "LOADCASE", "CONSTRAINTMETHOD", "ELASTIC",
    "SHELLSECTION", "FIELD", "ORIENTATION", "AMPLITUDE", "DAMPING",
    "WRITEEVERY", "COUPLING", "CONNECTOR",
}
_REQUIRED_ALIASES = {
    ("NSET", "NSET"): {"NSET", "NAME"},
    ("ELSET", "ELSET"): {"ELSET", "NAME"},
    ("SFSET", "SFSET"): {"SFSET", "NAME"},
}
_SOLVER_OPTIONS = {
    "DEVICE": {"CPU", "GPU"},
    "METHOD": {"DIRECT", "ITERATIVE"},
}


def validate_deck(text: str) -> list[str]:
    errors = []
    for number, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line.startswith("*") or line.startswith("**"):
            continue
        parts = [part.strip() for part in line[1:].split(",")]
        name = parts[0].upper()
        spec = ALL_COMMANDS.get(name)
        if spec is None:
            errors.append(f"Line {number}: unknown FEMaster command *{name}")
            continue
        keywords = _keywords(parts[1:])
        unknown = set(keywords) - spec.keywords
        if unknown:
            errors.append(
                f"Line {number}: *{name} unknown keyword(s): "
                + ", ".join(sorted(unknown))
            )
        missing = {
            required for required in spec.required
            if not (_REQUIRED_ALIASES.get((name, required), {required}) & set(keywords))
        }
        if missing:
            errors.append(
                f"Line {number}: *{name} missing keyword(s): "
                + ", ".join(sorted(missing))
            )
        errors.extend(_variant_errors(number, name, spec, keywords))
    return errors


def require_valid(text: str) -> None:
    errors = validate_deck(text)
    if errors:
        raise FEMasterSyntaxError("\n".join(errors))


def _keywords(tokens):
    values = {}
    for token in tokens:
        key, separator, value = token.partition("=")
        values[key.upper()] = value.upper() if separator else ""
    return values


def _variant_errors(number, name, spec, keywords):
    errors = []
    if name == "ELEMENT":
        value = keywords.get("TYPE", "")
        if value not in ELEMENT_TYPES:
            errors.append(f"Line {number}: unsupported FEMaster element type {value}")
    elif name == "SOLVER":
        for key, allowed in _SOLVER_OPTIONS.items():
            value = keywords.get(key)
            if value and value not in allowed:
                errors.append(f"Line {number}: *SOLVER invalid {key}={value}")
    elif name == "HYPERELASTIC":
        if not set(keywords) & spec.keywords:
            errors.append(f"Line {number}: *HYPERELASTIC requires NEO HOOKE")
    elif name in _TYPE_COMMANDS and spec.variants:
        value = keywords.get("TYPE")
        if value and value not in spec.variants:
            errors.append(f"Line {number}: *{name} invalid TYPE={value}")
    return errors
