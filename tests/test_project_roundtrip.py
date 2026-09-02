"""Current-schema project persistence round-trip regressions."""

import tempfile
import unittest
from pathlib import Path

from opencae.model.core import EntityRef
from opencae.model.entities.amplitudes import Amplitude
from opencae.model.entities.fields import FieldDefinition
from opencae.model.entities.jobs import ResultField, ResultSet
from opencae.model.entities.loads import ConcentratedLoad, TemperatureLoad
from opencae.model.entities.supports import DisplacementSupport
from opencae.model.selection import RegionProjection, named_region_definition
from opencae.persistence.project_io import load_project, save_project
from tests.test_femaster_dsl import _project


class ProjectRoundTripTest(unittest.TestCase):
    """Verify current canonical entities survive one JSON persistence cycle."""

    def test_mesh_membership_survives_json(self):
        """Mesh topology caches and shared AnalysisStep references survive save/load."""
        project = _project()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.ocae"
            save_project(project, path)
            loaded = load_project(path)
        self.assertEqual([1, 2, 3], loaded.parts[0].mesh.entity_nodes["Face-1"])
        self.assertEqual([1], loaded.parts[0].mesh.entity_elements["Cell-1"])
        self.assertEqual(
            "Linear Static",
            loaded.analyses[0].resolved_steps(loaded)[0].step_type,
        )

    def test_new_load_support_and_result_types_survive_json(self):
        """Current typed loads, supports, amplitudes, fields and results round-trip."""
        project = _project()
        target = next(
            region
            for region in project.assembly.regions
            if region.preferred_projection == RegionProjection.NODES
        )
        target_definition = named_region_definition(target)
        temperature = FieldDefinition(name="T")
        amplitude = Amplitude(
            name="RAMP",
            points=[(0.0, 0.0), (0.5, 1.0), (1.0, 0.25)],
            interpolation="Smooth Step",
            time_basis="Total time",
        )
        project.fields.append(temperature)
        project.amplitudes = [amplitude]
        project.loads = [
            ConcentratedLoad(
                name="CLOAD",
                target=target_definition,
                components=[1, 2, 3, 4, 5, 6],
                amplitude_ref=EntityRef.of(amplitude),
            ),
            TemperatureLoad(
                name="TEMP",
                temperature_field_ref=EntityRef.of(temperature),
                reference_temperature=20.0,
            ),
        ]
        project.supports = [
            DisplacementSupport(
                name="BC",
                target=target_definition,
                components=[0.0, None, 1.0, None, None, None],
            ),
        ]
        project.steps[0].load_refs = [EntityRef.of(load, "Load") for load in project.loads]
        project.steps[0].support_refs = [
            EntityRef.of(support, "Support") for support in project.supports
        ]
        project.results = [
            ResultSet(
                name="R",
                source_file="r.frd",
                fields=[ResultField(name="DISP", location="Nodal", components=3)],
            )
        ]
        project.rebuild_index(strict=True)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.ocae"
            save_project(project, path)
            loaded = load_project(path)
        self.assertIsInstance(loaded.loads[0], ConcentratedLoad)
        self.assertEqual([1, 2, 3, 4, 5, 6], loaded.loads[0].components)
        self.assertEqual("RAMP", loaded.amplitudes[0].name)
        self.assertEqual("Smooth Step", loaded.amplitudes[0].interpolation)
        self.assertEqual("Total time", loaded.amplitudes[0].time_basis)
        self.assertEqual(loaded.amplitudes[0].id, loaded.loads[0].amplitude_ref.entity_id)
        self.assertIs(loaded.loads[0].amplitude, loaded.amplitudes[0])
        self.assertIsInstance(loaded.supports[0], DisplacementSupport)
        self.assertEqual("DISP", loaded.results[0].fields[0].name)


if __name__ == "__main__":
    unittest.main()
