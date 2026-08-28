from pathlib import Path
from tempfile import TemporaryDirectory

from opencae.controllers.part.lifecycle import _apply_imported_regions
from opencae.geometry.mesh_import import read_mesh, read_mesh_with_report
from opencae.model.part import Part
from opencae.model.selection import RegionProjection
from opencae.controllers.part.mesh_persistence import apply_mesh_snapshot


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
        path = Path(directory) / "mesh.inp"
        path.write_text(deck)
        snapshot = read_mesh(path, "part-id")
    assert list(snapshot.node_tags) == [1, 2, 3, 4]
    assert snapshot.element_count == 1
    assert list(snapshot.blocks[0].element_tags) == [10]
    assert snapshot.blocks[0].connectivity.tolist() == [[0, 1, 2, 3]]


def test_inp_import_reports_every_keyword_block_that_was_not_imported():
    deck = """*HEADING
Example model
*NODE, NSET=ALL_NODES
1, 0, 0, 0
2, 1, 0, 0
3, 0, 1, 0
4, 0, 0, 1
*ELEMENT, TYPE=C3D4, ELSET=SOLID
10, 1, 2, 3, 4
*NSET, NSET=FIXED
1, 2
*ELSET, ELSET=BODY
SOLID
*SURFACE, NAME=LOAD_FACE, TYPE=ELEMENT
BODY, S1
*MATERIAL, NAME=Steel
*ELASTIC
210000, 0.3
*STEP, NLGEOM=YES
*BOUNDARY
FIXED, 1, 3
*END STEP
"""
    with TemporaryDirectory() as directory:
        path = Path(directory) / "model.inp"
        path.write_text(deck)
        imported = read_mesh_with_report(path, "part-id")

    assert imported.node_sets["ALL_NODES"] == (1, 2, 3, 4)
    assert imported.node_sets["FIXED"] == (1, 2)
    assert imported.element_sets["SOLID"] == (10,)
    assert imported.element_sets["BODY"] == (10,)
    assert imported.surfaces["LOAD_FACE"] == ((10, "S1"),)

    issues = imported.report.not_imported
    assert [issue.keyword for issue in issues] == [
        "HEADING",
        "MATERIAL",
        "ELASTIC",
        "STEP",
        "BOUNDARY",
        "END STEP",
    ]
    assert [issue.line_number for issue in issues] == [1, 16, 17, 19, 20, 22]
    formatted = imported.report.format_unimported()
    assert "*MATERIAL, NAME=Steel — line 16" in formatted
    assert "*BOUNDARY — line 20" in formatted
    assert "keyword is not supported by the orphan-mesh importer" in formatted


def test_inp_import_reports_unsupported_element_block_without_hiding_other_mesh():
    deck = """*NODE
1, 0, 0, 0
2, 1, 0, 0
3, 0, 1, 0
4, 0, 0, 1
*ELEMENT, TYPE=C3D4
10, 1, 2, 3, 4
*ELEMENT, TYPE=CAX4
20, 1, 2, 3, 4
"""
    with TemporaryDirectory() as directory:
        path = Path(directory) / "mixed.inp"
        path.write_text(deck)
        imported = read_mesh_with_report(path, "part-id")

    assert imported.snapshot.element_count == 1
    assert len(imported.report.not_imported) == 1
    issue = imported.report.not_imported[0]
    assert issue.keyword == "ELEMENT"
    assert issue.header == "*ELEMENT, TYPE=CAX4"
    assert "TYPE=CAX4" in issue.reason


def test_inp_sets_and_surfaces_become_object_backed_part_regions():
    deck = """*NODE
1, 0, 0, 0
2, 1, 0, 0
3, 0, 1, 0
4, 0, 0, 1
*ELEMENT, TYPE=C3D4, ELSET=BODY
10, 1, 2, 3, 4
*NSET, NSET=FIXED
1, 2
*SURFACE, NAME=FACE, TYPE=ELEMENT
BODY, S1
"""
    with TemporaryDirectory() as directory:
        path = Path(directory) / "regions.inp"
        path.write_text(deck)
        part = Part(name="Imported", source_type="Orphan Mesh")
        imported = read_mesh_with_report(path, part.id)
        apply_mesh_snapshot(part, imported.snapshot)
        _apply_imported_regions(part, imported)

    by_name = {region.name: region for region in part.regions}
    assert by_name["FIXED"].preferred_projection == RegionProjection.NODES
    assert by_name["BODY"].preferred_projection == RegionProjection.ELEMENTS
    assert by_name["FACE"].preferred_projection == RegionProjection.FACETS
    assert [item.operand.node_id for item in by_name["FIXED"].definition.items] == [1, 2]
    assert [item.operand.element_id for item in by_name["BODY"].definition.items] == [10]
    facet = by_name["FACE"].definition.items[0].operand
    assert (facet.element_id, facet.local_face) == (10, "S1")
    assert facet.owner_ref.entity_id == part.id
