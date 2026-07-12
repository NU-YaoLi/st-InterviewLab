"""Tests for interview completion detection and ephemeral TTL helpers."""

from __future__ import annotations

import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bknd.interviewlab_completion import looks_like_interview_end
from bknd.interviewlab_engine import InterviewState
from bknd.interviewlab_realtime import (
    build_realtime_instructions,
    ephemeral_key_is_fresh,
    ephemeral_ttl_seconds,
)


class InterviewEndDetectionTests(unittest.TestCase):
    def test_exact_closing_phrase(self) -> None:
        self.assertTrue(looks_like_interview_end("This interview has concluded."))

    def test_wrap_up_variant(self) -> None:
        self.assertTrue(
            looks_like_interview_end(
                "Great answers today. That wraps up our interview — good luck!"
            )
        )

    def test_thanks_and_goodbye(self) -> None:
        self.assertTrue(
            looks_like_interview_end(
                "Thank you for your time today. Goodbye and good luck."
            )
        )

    def test_mid_interview_thanks_is_not_end(self) -> None:
        self.assertFalse(
            looks_like_interview_end("Thanks, that helps. What was the result?")
        )

    def test_empty_is_not_end(self) -> None:
        self.assertFalse(looks_like_interview_end(""))
        self.assertFalse(looks_like_interview_end("Got it."))


class EphemeralTtlTests(unittest.TestCase):
    def test_ttl_covers_duration_plus_buffer(self) -> None:
        ttl = ephemeral_ttl_seconds(45)
        self.assertGreaterEqual(ttl, 45 * 60)
        self.assertLessEqual(ttl, 7200)

    def test_ttl_clamped_to_api_max(self) -> None:
        self.assertEqual(ephemeral_ttl_seconds(200), 7200)

    def test_freshness_check(self) -> None:
        self.assertTrue(ephemeral_key_is_fresh(int(time.time()) + 600))
        self.assertFalse(ephemeral_key_is_fresh(int(time.time()) - 10))
        self.assertFalse(ephemeral_key_is_fresh(None))


class ReconnectInstructionsTests(unittest.TestCase):
    def test_mid_session_instructions_skip_welcome(self) -> None:
        state = InterviewState()
        state.chat_history = [
            {"role": "assistant", "content": "Tell me about a challenge."},
            {"role": "user", "content": "I led a migration."},
        ]
        text = build_realtime_instructions(state)
        self.assertIn("Mid-session reconnect", text)
        self.assertIn("Do NOT restart with a welcome", text)


if __name__ == "__main__":
    unittest.main()
