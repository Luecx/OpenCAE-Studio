import unittest

from opencae.model.core import DeckWriter, ExportContext
from opencae.model.entities.fields import FieldDefinition
from opencae.model.entities.project import Project
from opencae.solvers.femaster_dsl.emitters.fields import write_field
from opencae.solvers.femaster_dsl.validator import validate_deck


class FemasterFieldTest(unittest.TestCase):
    def test_element_nodal_domain(self):
        field = FieldDefinition(
            name="EN", location="Element-Nodal", components=2,
            source_type="Tabular", table=[["1", "0", "2.5", "3.5"]],
        )
        writer = DeckWriter()
        write_field(field, writer, ExportContext(Project(name="P")))
        deck = writer.text()
        self.assertIn("*FIELD, NAME=EN, TYPE=ELEMENT_NODAL, COLS=2, FILL=NAN", deck)
        self.assertFalse(validate_deck(deck))

    def test_material_point_domain(self):
        field = FieldDefinition(
            name="MP",
            location="Material Point",
            components=1,
            source_type="Tabular",
            table=[["42", "0", "1", "0.15"]],
        )
        writer = DeckWriter()
        write_field(field, writer, ExportContext(Project(name="P")))
        deck = writer.text()
        self.assertIn("*FIELD, NAME=MP, TYPE=ELEMENT_MP, COLS=1, FILL=NAN", deck)
        self.assertIn("42, 0, 1, 0.15", deck)
        self.assertFalse(validate_deck(deck))

    def test_shell_normal_registers_three_component_element_nodal_field(self):
        field = FieldDefinition(
            name="SHELL_NORMALS",
            location="Shell Normal",
            components=3,
            source_type="Tabular",
            table=[["42", "0", "0", "0", "1"]],
        )
        writer = DeckWriter()
        write_field(field, writer, ExportContext(Project(name="P")))
        deck = writer.text()
        self.assertIn(
            "*FIELD, NAME=SHELL_NORMALS, TYPE=ELEMENT_NODAL, COLS=3, FILL=NAN",
            deck,
        )
        self.assertIn("*NORMAL, FIELD=SHELL_NORMALS", deck)
        self.assertFalse(validate_deck(deck))

    def test_shell_normal_requires_three_components(self):
        field = FieldDefinition(name="BAD", location="Shell Normal", components=2)
        with self.assertRaisesRegex(ValueError, "exactly three components"):
            write_field(field, DeckWriter(), ExportContext(Project(name="P")))


if __name__ == "__main__": unittest.main()
