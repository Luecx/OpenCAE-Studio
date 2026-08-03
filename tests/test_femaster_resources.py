import unittest

from opencae.model.core import DeckWriter, EntityRef, ExportContext
from opencae.model.entities.parts.part import Part
from opencae.model.entities.project import Project
from opencae.model.entities.resources.material import Material
from opencae.model.entities.resources.material_behaviors import NeoHookeElasticity
from opencae.model.entities.sections.beam import BeamSection
from opencae.model.entities.sections.shell import ShellSection
from opencae.model.entities.sections.truss import TrussSection
from opencae.solvers.femaster_dsl.emitters.resources import write_material, write_section
from opencae.solvers.femaster_dsl.validator import validate_deck


class FEMasterResourceTest(unittest.TestCase):
    def test_exact_material_and_section_syntax(self):
        writer = DeckWriter()
        context = ExportContext(Project(name="SYNTAX"), None)
        write_material(Material(
            name="RUBBER",
            behaviors=[NeoHookeElasticity(c10=0.35, d1=0.02)],
        ), writer, context)
        write_section(
            TrussSection(name="TRUSS", material_ref=EntityRef(legacy_name="STEEL"), area=25.0),
            "BRACES", "Global", writer, context,
        )
        write_section(
            BeamSection(
                name="BEAM", material_ref=EntityRef(legacy_name="STEEL"), profile_ref=EntityRef(legacy_name="RECT"),
                direction=(0.0, 0.0, 1.0),
            ),
            "FRAME", "Global", writer, context,
        )
        write_section(_abd_shell(), "SKIN", "Global", writer, context)
        deck = writer.text()
        self.assertFalse(validate_deck(deck))
        self.assertIn("*HYPERELASTIC, NEO HOOKE\n0.35, 0.02", deck)
        self.assertIn("*TRUSSSECTION, ELSET=BRACES, MATERIAL=STEEL, AREA=25", deck)
        self.assertIn(
            "*BEAMSECTION, ELSET=FRAME, MATERIAL=STEEL, PROFILE=RECT\n0, 0, 1",
            deck,
        )
        self.assertIn("31, 32, 33, 34, 35, 36\n101, 102, 103, 104", deck)


def _abd_shell():
    return ShellSection(
        name="ABD",
        shell_definition="ABD shell section",
        thickness=1.0,
        abd_matrix=[[float(i * 6 + j + 1) for j in range(6)] for i in range(6)],
        shear_matrix=[[101.0, 102.0], [103.0, 104.0]],
    )


if __name__ == "__main__":
    unittest.main()
