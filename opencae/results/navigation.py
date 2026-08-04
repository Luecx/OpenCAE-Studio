from opencae.model.entities.jobs import ResultField


def step_ids(fields):
    return list(dict.fromkeys(int(field.metadata.get("step_id", 1)) for field in fields))


def step_label(result, step_id, index):
    names = result.metadata.get("step_names", ()) if hasattr(result, "metadata") else ()
    if isinstance(names, dict):
        return str(names.get(str(step_id), names.get(step_id, f"Step {index + 1}")))
    if index < len(names):
        return str(names[index])
    return f"Step {index + 1}"


def frame_keys(fields, step_id):
    values = {
        (int(field.metadata.get("frame_id", 1)), float(field.metadata.get("frame_value", 0.0)))
        for field in fields
        if int(field.metadata.get("step_id", 1)) == step_id
    }
    return sorted(values, key=lambda item: (item[0], item[1]))


def frame_label(frame_id, value):
    return f"Frame {frame_id} — {value:.6g}"


def fields_for(fields, step_id, frame_id):
    return [
        field for field in fields
        if int(field.metadata.get("step_id", 1)) == step_id
        and int(field.metadata.get("frame_id", 1)) == frame_id
    ]


def display_field(source, component):
    return ResultField(
        name=source.name,
        location=source.location,
        components=1,
        metadata={**source.metadata, "block": source.name, "component": component},
    )
