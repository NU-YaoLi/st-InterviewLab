"""Tests for per-question eval alignment, reports, and interview history."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _OpenAI:
        pass

    class _OpenAIError(Exception):
        pass

    openai_stub.OpenAI = _OpenAI
    openai_stub.OpenAIError = _OpenAIError
    sys.modules["openai"] = openai_stub

from bknd.interviewlab_engine import InterviewState
from bknd.interviewlab_evaluator import (
    _parse_evaluation_json,
    align_turn_evaluations,
    evaluate_full_interview,
)
from bknd.interviewlab_history import (
    build_history_entry,
    history_score_series,
    upsert_history_entry,
)
from bknd.interviewlab_report import (
    build_markdown_report,
    build_pdf_report,
    payload_from_session,
    report_filename,
)


class TurnAlignmentTests(unittest.TestCase):
    def test_aligns_model_turns_to_responses(self) -> None:
        responses = [
            {
                "question_index": 1,
                "question": "Tell me about a challenge.",
                "answer": "I led a migration.",
                "is_follow_up": False,
            },
            {
                "question_index": 1,
                "question": "What was the result?",
                "answer": "Latency dropped 30%.",
                "is_follow_up": True,
            },
        ]
        raw = [
            {
                "overall_score": 80,
                "dimension_scores": {"communication_clarity": 8},
                "feedback": "Clear story.",
            },
            {
                "overall_score": 70,
                "dimension_scores": {"structure": 7},
                "feedback": "Add more metrics.",
            },
        ]
        aligned = align_turn_evaluations(raw, responses)
        self.assertEqual(len(aligned), 2)
        self.assertTrue(aligned[0]["scored"])
        self.assertTrue(aligned[1]["is_follow_up"])
        self.assertEqual(aligned[0]["overall_score"], 80)
        self.assertEqual(aligned[1]["feedback"], "Add more metrics.")
        self.assertEqual(aligned[0]["dimension_scores"]["communication_clarity"], 8)

    def test_missing_model_turns_are_unscored_placeholders(self) -> None:
        responses = [
            {
                "question_index": 1,
                "question": "Q",
                "answer": "A",
                "is_follow_up": False,
            }
        ]
        aligned = align_turn_evaluations([], responses)
        self.assertEqual(len(aligned), 1)
        self.assertFalse(aligned[0]["scored"])
        self.assertEqual(aligned[0]["question"], "Q")

    def test_parse_json_includes_turn_evaluations(self) -> None:
        raw = """
        {
          "overall_score": 75,
          "dimension_scores": {"communication_clarity": 8, "technical_logical_accuracy": 7, "structure": 7},
          "strengths": ["Clear"],
          "improvements": ["Metrics"],
          "sample_answer": "I led the work.",
          "turn_evaluations": [{"overall_score": 78, "feedback": "Solid."}]
        }
        """
        responses = [
            {
                "question_index": 1,
                "question": "Challenge?",
                "answer": "Migration.",
                "is_follow_up": False,
            }
        ]
        result = _parse_evaluation_json(raw, responses)
        self.assertEqual(result["overall_score"], 75)
        self.assertEqual(len(result["turn_evaluations"]), 1)
        self.assertEqual(result["turn_evaluations"][0]["overall_score"], 78)

    def test_empty_interview_has_no_turn_scores(self) -> None:
        result = evaluate_full_interview(None, InterviewState())  # type: ignore[arg-type]
        self.assertEqual(result["turn_evaluations"], [])


class HistoryTests(unittest.TestCase):
    def test_upsert_replaces_same_fingerprint(self) -> None:
        entry1 = build_history_entry(
            mode="Behavioral",
            role_label="Backend Engineer",
            job_description="Backend Engineer",
            duration_minutes=15,
            evaluation_results={"overall_score": 60, "strengths": ["A"]},
            turn_evaluations=[],
            chat_history=[{"role": "user", "content": "I led a migration."}],
            answer_count=1,
            completed_at="2026-08-17T00:00:00+00:00",
        )
        entry2 = build_history_entry(
            mode="Behavioral",
            role_label="Backend Engineer",
            job_description="Backend Engineer",
            duration_minutes=15,
            evaluation_results={"overall_score": 80, "strengths": ["B"]},
            turn_evaluations=[],
            chat_history=[{"role": "user", "content": "I led a migration."}],
            answer_count=1,
            completed_at="2026-08-17T01:00:00+00:00",
        )
        self.assertEqual(entry1["fingerprint"], entry2["fingerprint"])
        history = upsert_history_entry([], entry1)
        history = upsert_history_entry(history, entry2)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["overall_score"], 80)

    def test_score_series_is_chronological(self) -> None:
        history = [
            {"overall_score": 40},
            {"overall_score": 70},
        ]
        self.assertEqual(history_score_series(history), [40, 70])


class ReportTests(unittest.TestCase):
    def _payload(self) -> dict:
        return {
            "completed_at": "2026-08-17T20:00:00+00:00",
            "mode": "Behavioral",
            "role_label": "Backend Engineer",
            "duration_minutes": 15,
            "overall_score": 72,
            "dimension_scores": {
                "communication_clarity": 8,
                "technical_logical_accuracy": 7,
                "structure": 6,
            },
            "strengths": ["Clear examples"],
            "improvements": ["Add metrics"],
            "sample_answer": "I led the migration and cut latency 30%.",
            "turn_evaluations": [
                {
                    "question_index": 1,
                    "question": "Tell me about a challenge.",
                    "answer": "I led a migration.",
                    "is_follow_up": False,
                    "overall_score": 80,
                    "dimension_scores": {
                        "communication_clarity": 8,
                        "technical_logical_accuracy": 8,
                        "structure": 7,
                    },
                    "feedback": "Strong opening.",
                    "scored": True,
                }
            ],
            "chat_history": [
                {"role": "assistant", "content": "Tell me about a challenge."},
                {"role": "user", "content": "I led a migration."},
            ],
            "answer_count": 1,
            "security_terminated": False,
        }

    def test_markdown_includes_score_rubric_and_transcript(self) -> None:
        md = build_markdown_report(self._payload())
        self.assertIn("# InterviewLab Report", md)
        self.assertIn("Overall score:** 72 / 100", md)
        self.assertIn("STAR Structure", md)
        self.assertIn("Clear examples", md)
        self.assertIn("Add metrics", md)
        self.assertIn("Per-question scores", md)
        self.assertIn("I led a migration.", md)
        self.assertIn("**Interviewer:** Tell me about a challenge.", md)

    def test_filename_uses_mode_score_and_date(self) -> None:
        name = report_filename(self._payload(), "md")
        self.assertEqual(name, "InterviewLab-Behavioral-72-2026-08-17.md")

    def test_payload_from_session(self) -> None:
        session = {
            "interview_mode": "Technical",
            "job_description": "SRE",
            "interview_duration_minutes": 20,
            "evaluation_results": {"overall_score": 55, "strengths": ["X"]},
            "turn_evaluations": [],
            "chat_history": [{"role": "user", "content": "I used Prometheus."}],
            "responses": [
                {
                    "question": "How do you monitor?",
                    "answer": "I used Prometheus.",
                    "is_follow_up": False,
                }
            ],
            "interview_completed_at": "2026-08-17T12:00:00+00:00",
        }
        payload = payload_from_session(session, role_label="SRE")
        self.assertEqual(payload["mode"], "Technical")
        self.assertEqual(payload["overall_score"], 55)
        self.assertEqual(payload["answer_count"], 1)

    def test_pdf_starts_with_pdf_header(self) -> None:
        try:
            pdf = build_pdf_report(self._payload())
        except ImportError:
            self.skipTest("fpdf2 is not installed")
        self.assertTrue(pdf.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
