import tempfile
import unittest
from pathlib import Path

from opencae.model.core import EntityRef, NodeSetTarget
from opencae.persistence.project_io import load_project, save_project
from tests.test_femaster_dsl import _project
from opencae.model.entities.fields import FieldDefinition
from opencae.model.entities.jobs import ResultField, ResultSet
from opencae.model.entities.loads import ConcentratedLoad, TemperatureLoad
from opencae.model.entities.supports import DisplacementSupport


class ProjectRoundTripTest(unittest.TestCase):
    def test_mesh_membership_survives_json(self):
        project = _project()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.ocae"
            save_project(project, path)
            loaded = load_project(path)
        self.assertEqual([1, 2, 3], loaded.parts[0].mesh.entity_nodes["Face-1"])
        self.assertEqual([1], loaded.parts[0].mesh.entity_elements["Cell-1"])
        self.assertEqual("Linear Static", loaded.analyses[0].steps[0].step_type)

    def test_new_load_support_and_result_types_survive_json(self):
        project = _project()
        target = project.assembly.node_sets[0]
        temperature = FieldDefinition(name="T")
        project.fields.append(temperature)
        project.loads = [
            ConcentratedLoad(name="CLOAD", target=NodeSetTarget(ref=EntityRef.of(target)), components=[1, 2, 3, 4, 5, 6]),
            TemperatureLoad(name="TEMP", temperature_field_ref=EntityRef.of(temperature), reference_temperature=20.0),
        ]
        project.supports = [
            DisplacementSupport(name="BC", target=NodeSetTarget(ref=EntityRef.of(target)), components=[0.0, None, 1.0, None, None, None]),
        ]
        project.results = [ResultSet(name="R", source_file="r.frd", fields=[ResultField(name="DISP", location="Nodal", components=3)])]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.ocae"
            save_project(project, path); loaded = load_project(path)
        self.assertIsInstance(loaded.loads[0], ConcentratedLoad)
        self.assertEqual([1, 2, 3, 4, 5, 6], loaded.loads[0].components)
        self.assertIsInstance(loaded.supports[0], DisplacementSupport)
        self.assertEqual("DISP", loaded.results[0].fields[0].name)


if __name__ == "__main__":
    unittest.main()
