import unittest
from pathlib import Path

from opencae.results.frd_parser import parse_frd


class FrdParserTest(unittest.TestCase):
    def test_supplied_femaster_frd(self):
        path = Path('/mnt/data/Job-1.frd')
        if not path.exists():
            self.skipTest('sample FRD is not available')
        data = parse_frd(path)
        fields = {field.name: field for field in data.fields}
        self.assertEqual(len(data.nodes), 9158)
        self.assertEqual(len(data.elements), 38339)
        self.assertIn('DISP', fields)
        self.assertIn('STRESS', fields)
        self.assertEqual(fields['DISP'].components[:3], ['D1', 'D2', 'D3'])
        self.assertEqual(len(fields['DISP'].values), 9158)


if __name__ == '__main__':
    unittest.main()
