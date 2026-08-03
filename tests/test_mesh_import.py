from pathlib import Path
from tempfile import TemporaryDirectory

from opencae.geometry.mesh_import import read_mesh


def test_orphan_inp_mesh_import():
    deck = """*NODE
1, 0, 0, 0
2, 1, 0, 0
3, 0, 1, 0
4, 0, 0, 1
*ELEMENT, TYPE=C3D4
10, 1, 2, 3, 4
"""
    with TemporaryDirectory() as directory:
        path = Path(directory) / "mesh.inp"; path.write_text(deck)
        snapshot = read_mesh(path, "part-id")
    assert list(snapshot.node_tags) == [1, 2, 3, 4]
    assert snapshot.element_count == 1
    assert list(snapshot.blocks[0].element_tags) == [10]
    assert snapshot.blocks[0].connectivity.tolist() == [[0, 1, 2, 3]]
