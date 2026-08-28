"""Regression coverage for reusable scalar amplitude definitions."""

import unittest

from opencae.model.entities.amplitudes import Amplitude, preview_points, sample_function


class AmplitudeTest(unittest.TestCase):
    def test_function_ramp_is_baked_to_linear_table(self):
        points = sample_function(
            "Ramp",
            {"start_value": -1.0, "end_value": 3.0},
            2.0,
            4.0,
            4,
        )
        self.assertEqual(5, len(points))
        self.assertEqual((2.0, -1.0), points[0])
        self.assertEqual((4.0, 3.0), points[-1])
        self.assertEqual((3.0, 1.0), points[2])

    def test_smooth_step_preview_preserves_knots_and_densifies(self):
        knots = [(0.0, 0.0), (1.0, 1.0), (2.0, 0.5)]
        points = preview_points(knots, "Smooth Step", samples_per_segment=8)
        self.assertEqual(knots[0], points[0])
        self.assertEqual(knots[-1], points[-1])
        self.assertGreater(len(points), len(knots))
        self.assertEqual((1.0, 1.0), points[8])

    def test_amplitude_requires_strictly_increasing_time(self):
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            Amplitude(
                name="Invalid",
                points=[(0.0, 0.0), (0.0, 1.0)],
            )

    def test_function_metadata_does_not_replace_authoritative_points(self):
        amplitude = Amplitude(
            name="Sine",
            points=[(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)],
            source_mode="Function",
            function_type="Sine",
            function_parameters={"amplitude": 1.0, "frequency": 1.0},
        )
        self.assertEqual(
            [(0.0, 0.0), (0.5, 1.0), (1.0, 0.0)],
            amplitude.points,
        )
        self.assertEqual("Function", amplitude.source_mode)


if __name__ == "__main__":
    unittest.main()
