from .labels import entity_label


def name_entities(gmsh, entities) -> None:
    for dimension, tags in entities.items():
        for tag in tags:
            try:
                gmsh.model.setEntityName(dimension, tag, entity_label(dimension, tag))
            except Exception:
                pass
