import logging

_LOG = logging.getLogger(__name__)

from .labels import entity_label


def name_entities(gmsh, entities) -> None:
    for dimension, tags in entities.items():
        for tag in tags:
            try:
                gmsh.model.setEntityName(dimension, tag, entity_label(dimension, tag))
            except Exception as exc:
                _LOG.debug("Could not name Gmsh entity (%s, %s): %s", dimension, tag, exc, exc_info=True)
