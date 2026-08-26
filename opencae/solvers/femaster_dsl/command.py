from __future__ import annotations


def command(writer, name, data=(), *, flags=(), record_key="", **keywords):
    """Emit one native command through a semantic writer when available."""
    semantic = getattr(writer, "command", None)
    if callable(semantic):
        semantic(
            name,
            data,
            flags=flags,
            keywords=keywords,
            record_key=record_key,
        )
        return

    options = [str(flag).upper() for flag in flags if str(flag).strip()]
    options.extend(
        f"{key.upper()}={format_value(value)}"
        for key, value in keywords.items()
        if value not in (None, "")
    )
    writer.line("*" + name.upper() + (", " + ", ".join(options) if options else ""))
    for row in data:
        writer.line(format_row(row))


def format_row(row):
    if isinstance(row, str):
        return row
    return ", ".join(format_value(value) for value in row)


def format_value(value):
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    if value is None:
        return "NAN"
    if isinstance(value, float):
        return f"{value:.15g}"
    return str(value)
