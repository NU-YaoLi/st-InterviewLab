"""Unit tests for transcript sync, timer, and empty-interview evaluation."""

from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Stub openai so evaluator imports work without the package installed.
if "openai" not in sys.modules:
    openai_stub = types.ModuleType("openai")

    class _OpenAI:  # noqa: D401
        pass

    class _OpenAIError(Exception):
        pass

    openai_stub.OpenAI = _OpenAI
    openai_stub.OpenAIError = _OpenAIError
    sys.modules["openai"] = openai_stub

from bknd.interviewlab_engine import InterviewState, begin_live_session, start_interview_timer
from bknd.interviewlab_evaluator import _parse_evaluation_json, evaluate_full_interview
from bknd.interviewlab_language import is_english_text
from bknd.interviewlab_resume import combine_resume_sources
from bknd.interviewlab_realtime import (
    build_realtime_instructions,
    build_realtime_session_config,
    sync_transcript_to_state,
)


class TranscriptSyncTests(unittest.TestCase):
    def test_pairs_questions_and_answers(self) -> None:
        state = InterviewState()
        sync_transcript_to_state(
            state,
            [
                {"role": "assistant", "content": "Tell me about a challenge."},
                {"role": "user", "content": "I led a migration under a tight deadline."},
                {"role": "assistant", "content": "What was the result?"},
                {"role": "user", "content": "We cut latency by 30%."},
            ],
        )
        self.assertEqual(len(state.responses), 2)
        self.assertFalse(state.responses[0]["is_follow_up"])
        self.assertTrue(state.responses[1]["is_follow_up"])
        self.assertEqual(state.responses[1]["answer"], "We cut latency by 30%.")

    def test_empty_transcript_has_no_answers(self) -> None:
        state = InterviewState()
        sync_transcript_to_state(
            state,
            [{"role": "assistant", "content": "Welcome. Tell me about yourself."}],
        )
        self.assertEqual(state.responses, [])


class EvaluationJsonParseTests(unittest.TestCase):
    def test_string_feedback_is_not_character_split(self) -> None:
        raw = """
        {
          "overall_score": 70,
          "dimension_scores": {
            "communication_clarity": 7,
            "technical_logical_accuracy": 7,
            "structure": 7
          },
          "strengths": "Clear examples",
          "improvements": "Add more metrics",
          "sample_answer": "I led the migration."
        }
        """
        result = _parse_evaluation_json(raw)
        self.assertEqual(result["strengths"], ["Clear examples"])
        self.assertEqual(result["improvements"], ["Add more metrics"])
        self.assertEqual(result["overall_score"], 70)

    def test_list_feedback_is_preserved(self) -> None:
        raw = """
        {
          "overall_score": 80,
          "dimension_scores": {},
          "strengths": ["A", "B"],
          "improvements": ["C"],
          "sample_answer": ""
        }
        """
        result = _parse_evaluation_json(raw)
        self.assertEqual(result["strengths"], ["A", "B"])
        self.assertEqual(result["improvements"], ["C"])


class ResumeCombineTests(unittest.TestCase):
    def test_keeps_uploaded_text_when_notes_change(self) -> None:
        combined = combine_resume_sources(
            typed_text="Backend engineer, 5 years",
            uploaded_text="Jane Doe\nPython, AWS",
            uploaded_name="jane.pdf",
        )
        self.assertIn("jane.pdf", combined)
        self.assertIn("Python, AWS", combined)
        self.assertIn("Backend engineer", combined)


class EnglishDetectionTests(unittest.TestCase):
    def test_digit_only_answers_are_english(self) -> None:
        self.assertTrue(is_english_text("50"))
        self.assertTrue(is_english_text("100%"))
        self.assertTrue(is_english_text("2024"))

    def test_non_english_script_and_phrases(self) -> None:
        self.assertFalse(is_english_text("こんにちは"))
        self.assertFalse(is_english_text("Bonjour, merci beaucoup"))
        self.assertTrue(is_english_text("I led a migration under a tight deadline."))


class EmptyEvaluationTests(unittest.TestCase):
    def test_no_answers_scores_zero_without_client(self) -> None:
        state = InterviewState(
            resume="Expert in SQL, Spark, AWS",
            job_description="Data Engineer",
        )
        result = evaluate_full_interview(None, state)  # type: ignore[arg-type]
        self.assertEqual(result["overall_score"], 0)
        self.assertEqual(result["dimension_scores"]["communication_clarity"], 0)


class TimerTests(unittest.TestCase):
    def test_timer_starts_only_on_connect(self) -> None:
        state = InterviewState(interview_duration_minutes=20)
        begin_live_session(state)
        self.assertTrue(state.interview_session_started)
        self.assertIsNone(state.interview_started_at)
        start_interview_timer(state)
        self.assertIsNotNone(state.interview_started_at)


class RealtimeTurnTakingConfigTests(unittest.TestCase):
    def test_create_response_disabled_for_manual_turn_taking(self) -> None:
        cfg = build_realtime_session_config(InterviewState())
        turn = cfg["session"]["audio"]["input"]["turn_detection"]
        self.assertFalse(turn["create_response"])

    def test_instructions_require_one_question_then_wait(self) -> None:
        text = build_realtime_instructions(InterviewState())
        self.assertIn("ONE interview question per speaking turn", text)
        self.assertIn("Never ask a second interview question", text)


if __name__ == "__main__":
    unittest.main()
