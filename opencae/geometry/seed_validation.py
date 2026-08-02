from .labels import parse_labels
from .seeding import _divisions


def edge_seed_mismatches(gmsh, part):
    result = {}
    available = {tag for _, tag in gmsh.model.getEntities(1)}
    for seed in part.mesh.seeds:
        if seed.seed_type != "Edge" or not seed.enabled: continue
        for _dim, tag in parse_labels(seed.targets, 1):
            if tag not in available: result[f"Edge-{tag}"] = (None, None); continue
            expected = _divisions(gmsh, seed, tag)
            _types, element_tags, _nodes = gmsh.model.mesh.getElements(1, tag)
            actual = sum(len(values) for values in element_tags)
            if actual != expected: result[f"Edge-{tag}"] = (expected, actual)
    return result
