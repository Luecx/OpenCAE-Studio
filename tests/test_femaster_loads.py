import unittest

from opencae.model.core import DeckWriter, EntityRef, ExportContext, TargetKind, entity_target
from opencae.model.entities.loads import ConcentratedLoad, DistributedLoad, InertiaLoad, PressureLoad, TemperatureLoad, VolumeLoad
from opencae.model.entities.project import Project
from opencae.model.entities.supports import DisplacementSupport, FixedSupport


class FemasterLoadsTest(unittest.TestCase):
    def setUp(self):
        self.project = Project(name="LOADS")
        self.context = ExportContext(self.project, None)
        self.context.options["region_aliases"] = {"NODES": "NODES", "SURFACE": "SURFACE", "VOLUME": "VOLUME"}

    def render(self, entity):
        writer = DeckWriter(); entity.write_femaster(writer, self.context); return writer.text()

    def test_support_components(self):
        support = DisplacementSupport(name="BC", target=entity_target(EntityRef(legacy_name="NODES"), TargetKind.NODE_SET), components=[0.0, None, 2.0, None, None, 0.0])
        self.assertIn("NODES, 0, NAN, 2, NAN, NAN, 0", self.render(support))
        fixed = FixedSupport(name="FIX", target=entity_target(EntityRef(legacy_name="NODES"), TargetKind.NODE_SET), components=[0.0, 0.0, 0.0, None, None, None])
        self.assertIn("NODES, 0, 0, 0, NAN, NAN, NAN", self.render(fixed))

    def test_documented_load_commands(self):
        entities = [
            ConcentratedLoad(name="C", target=entity_target(EntityRef(legacy_name="NODES"), TargetKind.NODE_SET), components=[1, 2, 3, 4, 5, 6]),
            DistributedLoad(name="D", target=entity_target(EntityRef(legacy_name="SURFACE"), TargetKind.SURFACE), components=[1, 2, 3]),
            PressureLoad(name="P", target=entity_target(EntityRef(legacy_name="SURFACE"), TargetKind.SURFACE), pressure=7.0),
            VolumeLoad(name="V", target=entity_target(EntityRef(legacy_name="VOLUME"), TargetKind.ELEMENT_SET), components=[4, 5, 6]),
            TemperatureLoad(name="T", temperature_field_ref=EntityRef(legacy_name="TEMP"), reference_temperature=20.0),
            InertiaLoad(name="I", target=entity_target(EntityRef(legacy_name="VOLUME"), TargetKind.ELEMENT_SET), center=(1, 2, 3), center_acceleration=(4, 5, 6), angular_velocity=(7, 8, 9), angular_acceleration=(10, 11, 12), consider_point_masses=True),
        ]
        deck = "".join(self.render(entity) for entity in entities)
        self.assertIn("*CLOAD, LOAD_COLLECTOR=C\nNODES, 1, 2, 3, 4, 5, 6", deck)
        self.assertIn("*DLOAD, LOAD_COLLECTOR=D\nSURFACE, 1, 2, 3", deck)
        self.assertIn("*PLOAD, LOAD_COLLECTOR=P\nSURFACE, 7", deck)
        self.assertIn("*VLOAD, LOAD_COLLECTOR=V\nVOLUME, 4, 5, 6", deck)
        self.assertIn("*TLOAD, LOAD_COLLECTOR=T, TEMPERATUREFIELD=TEMP, REFERENCETEMPERATURE=20", deck)
        self.assertIn("*INERTIALOAD, LOAD_COLLECTOR=I, CONSIDER_POINT_MASSES=ON", deck)
        self.assertIn("VOLUME, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12", deck)


if __name__ == "__main__": unittest.main()
