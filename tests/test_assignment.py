import json
import sys
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import assignment


class AssignmentTests(unittest.TestCase):
    def test_mse_psnr_exact_and_known_error(self):
        reference = np.zeros((2, 2, 3), np.uint8)
        mse, psnr = assignment.mse_psnr(reference, reference.copy())
        self.assertEqual(mse, 0.0)
        self.assertTrue(np.isinf(psnr))
        changed = np.full_like(reference, 10)
        mse, psnr = assignment.mse_psnr(reference, changed)
        self.assertEqual(mse, 100.0)
        self.assertAlmostEqual(psnr, 10 * np.log10(255**2 / 100), places=8)

    def test_salt_pepper_is_deterministic_and_binary(self):
        frame = np.full((80, 100, 3), 127, np.uint8)
        first = assignment.add_salt_pepper(frame, np.random.default_rng(42), 0.1)
        second = assignment.add_salt_pepper(frame, np.random.default_rng(42), 0.1)
        self.assertTrue(np.array_equal(first, second))
        changed_values = set(np.unique(first[first != 127]).tolist())
        self.assertEqual(changed_values, {0, 255})

    def test_ffv1_writer_round_trip_is_exact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "exact.avi"
            frame = assignment.make_demo_frame(7)
            writer = assignment.open_writer(path, 24.0, assignment.FRAME_SIZE)
            writer.write(frame)
            writer.release()
            capture = cv2.VideoCapture(str(path))
            ok, decoded = capture.read()
            capture.release()
            self.assertTrue(ok)
            self.assertTrue(np.array_equal(frame, decoded))
            self.assertGreater(path.stat().st_size, 0)

    def test_generated_inputs_have_expected_video_contract(self):
        inputs = assignment.generate_inputs(force=False)
        video = inputs["generated_video"]
        self.assertEqual(video["frame_count"], assignment.FRAME_COUNT)
        self.assertAlmostEqual(video["fps"], assignment.FPS, places=3)
        self.assertEqual((video["width"], video["height"]), assignment.FRAME_SIZE)

    def test_metrics_json_if_present_has_self_describing_sections(self):
        if not assignment.METRICS_FILE.exists():
            self.skipTest("Full assignment has not been run yet")
        metrics = json.loads(assignment.METRICS_FILE.read_text(encoding="utf-8"))
        self.assertIn("environment", metrics)
        self.assertIn("inputs", metrics)
        for number in range(1, 11):
            self.assertIn(f"q{number}", metrics)
            self.assertIn("outputs", metrics[f"q{number}"])


if __name__ == "__main__":
    unittest.main()
