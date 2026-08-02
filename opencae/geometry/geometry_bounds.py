def geometry_bounds(gmsh, entities):
    dimension = next((value for value in (3, 2, 1, 0) if entities[value]), None)
    if dimension is None:
        return None
    boxes = [gmsh.model.getBoundingBox(dimension, tag) for tag in entities[dimension]]
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        min(box[2] for box in boxes),
        max(box[3] for box in boxes),
        max(box[4] for box in boxes),
        max(box[5] for box in boxes),
    )
