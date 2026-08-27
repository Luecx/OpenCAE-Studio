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
            source_type="Tabular", table=[["1", "2.5", "3.5"]],
        )
        writer = DeckWriter()
        write_field(field, writer, ExportContext(Project(name="P")))
        deck = writer.text()
        self.assertIn("*FIELD, NAME=EN, TYPE=ELEMENT_NODAL, COLS=2, FILL=NAN", deck)
        self.assertFalse(validate_deck(deck))


if __name__ == "__main__": unittest.main()
