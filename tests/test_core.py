import concurrent.futures
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd
from clustering import DEFAULT_POINTS, kmeans_steps, validate_config
from charts import consensus, vote_counts
import storage


class AlgorithmTests(unittest.TestCase):
    def test_known_example_converges_to_expected_groups(self):
        frames = kmeans_steps(DEFAULT_POINTS)
        final = frames[-1]
        self.assertTrue(final.converged)
        self.assertEqual(final.labels.tolist(), [0, 2, 1, 0, 1, 1, 2, 0])
        np.testing.assert_allclose(final.centers, [[11/3, 9], [7, 13/3], [1.5, 3.5]])
        objectives = [f.inertia for f in frames if f.inertia is not None]
        self.assertTrue(all(b <= a + 1e-10 for a, b in zip(objectives, objectives[1:])))

    def test_assignment_uses_nearest_and_updates_use_mean(self):
        x = np.array(DEFAULT_POINTS)
        for frame in kmeans_steps(DEFAULT_POINTS):
            if frame.kind == "assign":
                np.testing.assert_array_equal(frame.labels, np.argmin(frame.distances, axis=1))
            if frame.kind == "update":
                for j, center in enumerate(frame.centers):
                    if np.any(frame.labels == j):
                        np.testing.assert_allclose(center, x[frame.labels == j].mean(axis=0))

    def test_k_options_and_invalid_data(self):
        for k in (2, 3, 4):
            self.assertEqual(len(kmeans_steps(DEFAULT_POINTS, k)[-1].centers), k)
        for points in ([[0, 0]]*8, [[float("nan"), 2]]*8, [[1, 2]]*7):
            with self.assertRaises(ValueError):
                validate_config(points, 3, [0, 3, 6])

    def test_consensus_does_not_break_ties_arbitrarily(self):
        counts = vote_counts([{"choices": [0]*8}, {"choices": [1]*8}], 3)
        self.assertEqual(consensus(counts).tolist(), [-1]*8)
        self.assertEqual(consensus(vote_counts([], 3)).tolist(), [-1]*8)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"CLUSTERLAB_DATA_DIR": self.temp.name, "ADMIN_PASSWORD": "test-admin-password"})
        self.env.start()
        storage.initialize()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_ballot_insert_update_and_wrong_password(self):
        self.assertFalse(storage.submit_ballot("DEMO", "Student-01", "secret1", [0]*8))
        self.assertTrue(storage.submit_ballot("DEMO", " student-01 ", "secret1", [1]*8))
        self.assertEqual(len(storage.ballots("DEMO")), 1)
        with self.assertRaises(ValueError):
            storage.submit_ballot("DEMO", "Student-01", "wrongpw", [2]*8)
        self.assertEqual(storage.ballots("DEMO")[0]["choices"], [1]*8)
        with storage.connect() as db:
            self.assertNotEqual(db.execute("SELECT pin_hash FROM ballots").fetchone()[0], "secret1")

    def test_invalid_and_closed_ballots_are_not_saved(self):
        for choices in ([None]*8, [0]*7, [4]*8):
            with self.assertRaises(ValueError):
                storage.submit_ballot("DEMO", "one", "secret1", choices)
        storage.set_open("DEMO", False)
        with self.assertRaises(ValueError):
            storage.submit_ballot("DEMO", "one", "secret1", [0]*8)
        self.assertEqual(storage.ballots("DEMO"), [])
        storage.set_open("DEMO", True)
        storage.submit_ballot("DEMO", "one", "secret1", [0]*8)
        self.assertEqual(len(storage.ballots("DEMO")), 1)

    def test_sessions_isolate_ballots_and_survive_initialization(self):
        code = storage.create_room("Second class", DEFAULT_POINTS, 2, [0, 6])
        storage.submit_ballot(code, "one", "secret1", [1]*8)
        storage.initialize()
        self.assertEqual(len(storage.ballots(code)), 1)
        self.assertEqual(storage.ballots("DEMO"), [])
        self.assertEqual(storage.get_room(code)["k"], 2)

    def test_concurrent_writes(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(lambda i: storage.submit_ballot("DEMO", str(i), "secret1", [i % 3]*8), range(16)))
        self.assertEqual(len(storage.ballots("DEMO")), 16)

    def test_admin_auth_and_throttling(self):
        self.assertTrue(storage.verify_admin("test-admin-password")[0])
        for _ in range(5):
            self.assertFalse(storage.verify_admin("wrong")[0])
        self.assertFalse(storage.verify_admin("test-admin-password")[0])

    def test_csv_escapes_formulas(self):
        csv = storage.safe_csv(pd.DataFrame({"student": ["=SUM(A1:A9)", "  +evil", "normal"]})).decode("utf-8-sig")
        self.assertIn("'=SUM", csv)
        self.assertIn("'  +evil", csv)


if __name__ == "__main__":
    unittest.main()
