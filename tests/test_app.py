import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
import storage


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {"CLUSTERLAB_DATA_DIR": self.temp.name, "ADMIN_PASSWORD": "test-admin-password"})
        self.env.start()
        self.app = AppTest.from_file(str(APP / "app.py"), default_timeout=30).run()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def assert_healthy(self):
        self.assertEqual(len(self.app.exception), 0, str(self.app.exception))

    def sign_in(self):
        self.app.radio(key="workspace").set_value("Admin dashboard").run()
        self.app.text_input(key="admin_password_input").set_value("test-admin-password")
        self.app.button(key="FormSubmitter:admin_login-Open dashboard →").click().run()
        self.assert_healthy()

    def test_student_can_submit_complete_ballot(self):
        self.assert_healthy()
        text = {t.label: t for t in self.app.text_input}
        text["Student code or nickname"].set_value("test-student")
        text["Private ballot password"].set_value("ballot-secret")
        for name in "ABCDEFGH":
            self.app.selectbox(key=f"vote_DEMO_{name}").set_value(0)
        self.app.button(key="FormSubmitter:ballot_DEMO-Submit my eight votes →").click().run()
        self.assert_healthy()
        self.assertEqual(len(storage.ballots("DEMO")), 1)
        self.assertTrue(any("saved" in s.value for s in self.app.success))

    def test_admin_is_gated_and_slides_advance(self):
        self.app.radio(key="workspace").set_value("Admin dashboard").run()
        self.assertEqual(len(self.app.tabs), 0)
        self.sign_in()
        self.assertEqual([t.label for t in self.app.tabs], ["Overview", "All ballots", "K-means walkthrough", "Session controls"])
        self.app.button(key="next_DEMO").click().run()
        self.assert_healthy()
        self.assertEqual(self.app.session_state["slide_DEMO"], 1)
        self.app.button(key="toggle_voting").click().run()
        self.assertFalse(storage.get_room("DEMO")["is_open"])

    def test_session_creation_and_logout(self):
        self.sign_in()
        self.app.button(key="FormSubmitter:new_session-Create session →").click().run()
        self.assert_healthy()
        self.assertEqual(len(storage.rooms()), 2)
        self.assertNotEqual(self.app.selectbox(key="admin_room").value, "DEMO")
        next(b for b in self.app.button if b.label == "Sign out").click().run()
        self.assert_healthy()
        self.assertEqual(len(self.app.tabs), 0)


if __name__ == "__main__":
    unittest.main()
