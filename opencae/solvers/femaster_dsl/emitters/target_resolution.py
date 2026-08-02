from __future__ import annotations

from ..command import command


def entity_target_name(entity, kind, writer, context):
    aliases = context.options.get("entity_aliases", {})
    if entity.id in aliases:
        return aliases[entity.id]
    aliases = context.options.get("part_region_aliases", {}).get(entity.id, ())
    if len(aliases) == 1:
        return aliases[0]
    if len(aliases) > 1:
        return _merged_target(entity, kind, writer, context)
    raise ValueError(f"No exported target exists for {type(entity).__name__} '{entity.name}'")


def _merged_target(entity, kind, writer, context):
    cache = context.options.setdefault("merged_region_aliases", {})
    if entity.id in cache:
        return cache[entity.id]
    data = context.options.get("part_region_data", {}).get(entity.id, {})
    values = data.get("values", [])
    command_name = data.get("command") or ("NSET" if str(kind) in {"Node Set", "Reference Point"} else "ELSET")
    name = context.names.register(("merged-target", entity.id), f"__TARGET_{entity.name}")
    if command_name in {"NSET", "ELSET"}:
        unique = sorted({int(value) for value in values})
        if not unique:
            raise ValueError(f"Target '{entity.name}' does not contain exported {command_name} members")
        command(writer, command_name, [(value,) for value in unique], **{command_name: name})
    elif command_name == "SURFACE":
        start = int(context.options.get("next_surface_id", 1))
        rows = [(start + index, int(element_id), side) for index, (element_id, side) in enumerate(values)]
        if not rows:
            raise ValueError(f"Surface target '{entity.name}' has no exported members")
        command(writer, "SURFACE", rows, NAME=name)
        context.options["next_surface_id"] = start + len(rows)
    else:
        raise ValueError(f"Unsupported target command '{command_name}' for '{entity.name}'")
    cache[entity.id] = name
    return name
