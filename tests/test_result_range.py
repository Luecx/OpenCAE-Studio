from pathlib import Path
from tempfile import TemporaryDirectory

from opencae.results import FrdLoader


def test_scalar_range_reads_selected_component():
    content = """    2C
 -1         1 0.0 0.0 0.0
 -1         2 1.0 0.0 0.0
 -3
  100CL  101 1.00000E+00           1                     0    1           1
 -4  DISP
 -5  D1
 -5  D2
 -1         1 -2.0 0.0
 -1         2  4.0 0.0
 -3
"""
    with TemporaryDirectory() as directory:
        path = Path(directory) / "range.frd"; path.write_text(content)
        loader = FrdLoader(); field = loader.fields(path)[0]
        field.metadata["component"] = "D1"
        assert loader.scalar_range(path, field) == (-2.0, 4.0)
