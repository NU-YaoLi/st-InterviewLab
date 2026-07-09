"""
Interview state and timer helpers for live Realtime interviews.

Conversation turns are handled by OpenAI Realtime (WebRTC). This module keeps
the shared ``InterviewState`` model and countdown utilities used by the UI and
evaluation bridge.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from interviewlab_config import DEFAULT_DURATION_MINUTES, TOTAL_QUESTIONS


@dataclass
class InterviewContext:
    """Snapshot of setup fields for prompt construction."""

    mode: str
    target_role: str
    target_level: str
    job_description: str
    resume: str
    total_questions: int = TOTAL_QUESTIONS


@dataclass
class InterviewState:
    """Full mutable interview state (mirrors future DB schema)."""

    interview_active: bool = False
    interview_complete: bool = False
    interview_mode: str = "Behavioral"
    target_role: str = ""
    target_level: str = ""
    job_description: str = ""
    resume: str = ""
    chat_history: list[dict[str, str]] = field(default_factory=list)
    current_question_index: int = 0
    total_questions: int = TOTAL_QUESTIONS
    interview_duration_minutes: int = DEFAULT_DURATION_MINUTES
    interview_started_at: float | None = None
    interview_session_started: bool = False
    current_question_text: str = ""
    responses: list[dict[str, Any]] = field(default_factory=list)
    awaiting_follow_up: bool = False
    follow_up_count: int = 0
    scores: dict[str, Any] | None = None
    evaluation_results: dict[str, Any] | None = None
    turn_evaluations: list[dict[str, Any]] = field(default_factory=list)
    error_message: str | None = None

    def to_context(self) -> InterviewContext:
        return InterviewContext(
            mode=self.interview_mode,
            target_role=self.target_role,
            target_level=self.target_level,
            job_description=self.job_description,
            resume=self.resume,
            total_questions=self.total_questions,
        )


def add_message(state: InterviewState, role: str, content: str) -> None:
    """Append a chat message — single write path for future DB replacement."""
    state.chat_history.append({"role": role, "content": content})


def reset_interview_state(state: InterviewState) -> None:
    """Clear runtime interview data while preserving setup configuration."""
    state.interview_active = False
    state.interview_complete = False
    state.chat_history = []
    state.current_question_index = 0
    state.current_question_text = ""
    state.responses = []
    state.awaiting_follow_up = False
    state.follow_up_count = 0
    state.scores = None
    state.evaluation_results = None
    state.turn_evaluations = []
    state.error_message = None
    state.interview_started_at = None
    state.interview_session_started = False


def begin_live_session(state: InterviewState) -> None:
    """Mark the session ready. Countdown starts when WebRTC connects."""
    state.interview_session_started = True
    state.interview_started_at = None


def start_interview_timer(state: InterviewState) -> None:
    """Start the countdown once the live voice session is connected."""
    if state.interview_started_at is None:
        state.interview_started_at = time.time()


def context_block(ctx: InterviewContext) -> str:
    resume_text = ctx.resume or "(none provided)"
    job_text = ctx.job_description or ctx.target_role or "(none provided)"
    return (
        f"Interview mode: {ctx.mode}\n"
        f"Total main questions: {ctx.total_questions}\n\n"
        f"Job details (title, level, description):\n{job_text}\n\n"
        f"Candidate background (typed notes and/or uploaded resume):\n{resume_text}\n\n"
        "Important: Ask questions that connect the role requirements with this candidate's "
        "specific experience, skills, and projects whenever background information is available."
    )


def get_remaining_seconds(state: InterviewState) -> float:
    """Return seconds left in the interview, or full duration if not started."""
    if state.interview_started_at is None:
        return float(state.interview_duration_minutes * 60)
    elapsed = time.time() - state.interview_started_at
    return max(0.0, state.interview_duration_minutes * 60 - elapsed)


def is_time_expired(state: InterviewState) -> bool:
    """Return True when the interview timer has run out."""
    if not state.interview_session_started or state.interview_started_at is None:
        return False
    return get_remaining_seconds(state) <= 0


def get_time_progress(state: InterviewState) -> float:
    """Return 0.0–1.0 progress based on elapsed time."""
    total = state.interview_duration_minutes * 60
    if total <= 0:
        return 0.0
    if state.interview_started_at is None:
        return 0.0
    elapsed = time.time() - state.interview_started_at
    return min(elapsed / total, 1.0)


def format_remaining_time(state: InterviewState) -> str:
    """Format remaining time as MM:SS."""
    remaining = int(get_remaining_seconds(state))
    minutes, seconds = divmod(remaining, 60)
    return f"{minutes:02d}:{seconds:02d}"


def get_progress_fraction(state: InterviewState) -> float:
    """Return 0.0–1.0 progress based on time elapsed."""
    if state.interview_complete:
        return 1.0
    return get_time_progress(state)
