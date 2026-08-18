"""Tests for F5 setup persistence snapshots."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "streamlit" not in sys.modules:
    import types

    st = types.ModuleType("streamlit")
    st.session_state = {}
    sys.modules["streamlit"] = st

from fntnd.interviewlab_persist import apply_setup_snapshot, seed_setup_widget_keys, snapshot_setup


class SetupPersistTests(unittest.TestCase):
    def test_snapshot_round_trip_restores_job_and_resume(self) -> None:
        session = {
            "job_description": "Senior Backend Engineer\nPython, AWS",
            "resume_typed": "5 years backend",
            "resume_file_text": "Jane Doe\nPython",
            "resume_file_name": "jane.pdf",
            "resume_file_hash": "abc123",
            "resume": "Uploaded resume (jane.pdf):\nJane Doe\nPython",
            "interview_mode": "Technical",
            "interview_duration_minutes": 30,
            "interview_history": [{"overall_score": 80}],
            "realtime_ephemeral_key": "should-not-persist",
        }
        payload = snapshot_setup(session)
        self.assertNotIn("realtime_ephemeral_key", payload)
        self.assertEqual(payload["job_description"], session["job_description"])
        self.assertEqual(payload["resume_file_name"], "jane.pdf")

        restored: dict = {
            "job_description": "",
            "resume_file_text": "",
            "resume_file_name": "",
            "resume_file_hash": None,
            "resume": "",
            "resume_typed": "",
            "interview_mode": "Behavioral",
            "interview_duration_minutes": 15,
            "interview_history": [],
        }
        self.assertTrue(apply_setup_snapshot(restored, payload))
        self.assertEqual(restored["job_description"], "Senior Backend Engineer\nPython, AWS")
        self.assertEqual(restored["resume_file_text"], "Jane Doe\nPython")
        self.assertEqual(restored["resume_file_name"], "jane.pdf")
        self.assertEqual(restored["interview_mode"], "Technical")
        self.assertEqual(restored["interview_history"][0]["overall_score"], 80)
        restored["interview_history"][0]["overall_score"] = 1
        self.assertEqual(payload["interview_history"][0]["overall_score"], 80)

    def test_apply_ignores_invalid_payload(self) -> None:
        session = {"job_description": "keep me"}
        self.assertFalse(apply_setup_snapshot(session, None))
        self.assertFalse(apply_setup_snapshot(session, "nope"))  # type: ignore[arg-type]
        self.assertEqual(session["job_description"], "keep me")

    def test_seed_widget_keys_from_canonical_without_overwriting(self) -> None:
        session = {
            "job_description": "Restored job text",
            "resume_typed": "notes",
        }
        seed_setup_widget_keys(session)
        self.assertEqual(session["job_description_input"], "Restored job text")
        self.assertEqual(session["resume_typed_input"], "notes")
        session["job_description_input"] = "typed in widget"
        seed_setup_widget_keys(session)
        self.assertEqual(session["job_description_input"], "typed in widget")
        payload = snapshot_setup(session)
        self.assertNotIn("job_description_input", payload)


if __name__ == "__main__":
    unittest.main()
