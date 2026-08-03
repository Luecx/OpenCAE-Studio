from __future__ import annotations

import logging

_LOG = logging.getLogger(__name__)


def extract_entity_membership(gmsh):
    node_members = {}
    element_members = {}
    for dimension, tag in gmsh.model.getEntities():
        label = _label(dimension, tag)
        try:
            node_tags, _coordinates, _parameters = gmsh.model.mesh.getNodes(
                dimension, tag, True, False
            )
            node_members[label] = sorted({int(value) for value in node_tags})
        except Exception as exc:
            _LOG.warning("Could not read node membership for %s: %s", label, exc)
            node_members[label] = []
        try:
            _types, tag_blocks, _connectivity = gmsh.model.mesh.getElements(
                dimension, tag
            )
            element_members[label] = sorted(
                {int(value) for block in tag_blocks for value in block}
            )
        except Exception as exc:
            _LOG.warning("Could not read element membership for %s: %s", label, exc)
            element_members[label] = []
    return node_members, element_members


def _label(dimension, tag):
    names = {0: "Vertex", 1: "Edge", 2: "Face", 3: "Cell"}
    return f"{names.get(int(dimension), 'Entity')}-{int(tag)}"
