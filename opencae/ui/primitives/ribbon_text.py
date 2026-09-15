"""Shared ribbon caption normalization and wrapping."""

RIBBON_LABELS = {
    "Node Set": "NodeSet",
    "Element Set": "ElementSet",
    "Coordinate System": "CSYS",
    "Reference Point": "Ref Point",
}


def ribbon_label(text: str) -> tuple[str, bool]:
    """Return a compact ribbon caption and whether automatic wrapping is allowed."""
    clean = text.replace("…", "").strip()
    if clean.startswith("New "):
        return "New", False
    if clean.startswith("Duplicate "):
        return "Duplicate", False
    if clean in RIBBON_LABELS:
        return RIBBON_LABELS[clean], False
    return clean, True


def wrapped_ribbon_text(text: str) -> str:
    """Wrap a ribbon caption into at most two visually balanced lines."""
    clean = text.replace("…", "").strip()
    if "/" in clean and " " not in clean:
        left, right = clean.split("/", 1)
        if left and right:
            return f"{left}/\n{right}"

    words = clean.split()
    if len(words) <= 1:
        return clean
    if len(words) == 2:
        return "\n".join(words)

    midpoint = (len(words) + 1) // 2
    return " ".join(words[:midpoint]) + "\n" + " ".join(words[midpoint:])
