from opencae.geometry.element_summary import definition_from_block
from opencae.model.mesh import ElementBlock, NodeTable


def apply_mesh_snapshot(candidate, snapshot, definitions):
    candidate.mesh.nodes = NodeTable(
        ids=[int(value) for value in snapshot.node_tags],
        coordinates=[tuple(map(float, row)) for row in snapshot.points],
    )
    candidate.mesh.element_blocks = []
    candidate.mesh.entity_nodes = {key: list(values) for key, values in snapshot.entity_nodes.items()}
    candidate.mesh.entity_elements = {key: list(values) for key, values in snapshot.entity_elements.items()}
    next_id = 1
    for block in snapshot.blocks:
        if block.dimension != snapshot.dimension: continue
        ids = block.element_tags if block.element_tags is not None else range(next_id, next_id + len(block.connectivity))
        connectivity = [tuple(int(snapshot.node_tags[index]) for index in row) for row in block.connectivity]
        candidate.mesh.element_blocks.append(ElementBlock(
            definition=definition_from_block(block), ids=[int(value) for value in ids], connectivity=connectivity,
        ))
        next_id += len(block.connectivity)
    candidate.mesh.node_count = len(snapshot.points)
    candidate.mesh.element_count = sum(len(block.connectivity) for block in snapshot.blocks if block.dimension == snapshot.dimension)
    candidate.mesh.mesh_dimension = snapshot.dimension; candidate.mesh.elements = definitions; candidate.mesh.status = "Current"
    if snapshot.qualities is not None and len(snapshot.qualities):
        candidate.mesh.minimum_quality = float(snapshot.qualities.min())
        candidate.mesh.mean_quality = float(snapshot.qualities.mean())
