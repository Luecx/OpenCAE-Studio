from pathlib import Path
from tempfile import TemporaryDirectory

from opencae.results.frd_parser import parse_frd


def test_frd_parser_reads_nodes_elements_and_result_fields():
    content = """    2C
 -1         1 0.0 0.0 0.0
 -1         2 1.0 0.0 0.0
 -3
    3C
 -1        10 1
 -2         1 2
 -3
  100CL  1 0.0 1 0 1 1
 -4 DISP
 -5 D1
 -5 D2
 -5 D3
 -1         1 0.1 0.2 0.3
 -1         2 0.4 0.5 0.6
 -3
  100CL  1 0.0 1 0 1 1
 -4 STRESS
 -5 SXX
 -1         1 12.5
 -1         2 25.0
 -3
"""
    with TemporaryDirectory() as directory:
        path = Path(directory) / "sample.frd"
        path.write_text(content, encoding="utf-8")
        data = parse_frd(path)

    assert data.nodes == {
        1: (0.0, 0.0, 0.0),
        2: (1.0, 0.0, 0.0),
    }
    assert data.elements == [(10, 1, [1, 2])]

    fields = {field.name: field for field in data.fields}
    assert set(fields) == {"DISP", "STRESS"}
    assert fields["DISP"].components == ["D1", "D2", "D3"]
    assert fields["DISP"].values == {
        1: [0.1, 0.2, 0.3],
        2: [0.4, 0.5, 0.6],
    }
    assert fields["STRESS"].components == ["SXX"]
    assert fields["STRESS"].values == {
        1: [12.5],
        2: [25.0],
    }
