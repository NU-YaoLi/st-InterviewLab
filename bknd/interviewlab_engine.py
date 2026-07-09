"""
Interview conversation engine.

Manages state transitions, prompt construction, and LLM calls. Accepts plain
data structures rather than reading ``st.session_state`` directly so storage can
later be swapped for a database without rewriting core logic.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI, OpenAIError

from bknd.interviewlab_openai import create_chat_completion
from bknd.interviewlab_language import NON_ENGLISH_INTERVIEWER_REMINDER, is_english_text


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
    ai_voice_enabled: bool = True
    chat_history: list[dict[str, str]] = field(default_factory=list)
    current_question_index: int = 0
    total_questions: int = TOTAL_QUESTIONS
    interview_duration_minutes: int = DEFAULT_DURATION_MINUTES
    interview_started_at: float | None = None
    current_question_text: str = ""
    responses: list[dict[str, Any]] = field(default_factory=list)
    awaiting_follow_up: bool = False
    follow_up_count: int = 0
    scores: dict[str, Any] | None = None
    evaluation_results: dict[str, Any] | None = None
    turn_evaluations: list[dict[str, Any]] = field(default_factory=list)
    last_tts_audio: bytes | None = None
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
    state.last_tts_audio = None
    state.error_message = None
    state.interview_started_at = None


def _context_block(ctx: InterviewContext) -> str:
    return (
        f"Interview mode: {ctx.mode}\n"
        f"Total main questions: {ctx.total_questions}\n\n"
        f"Job details (title, level, description):\n"
        f"{ctx.job_description or ctx.target_role or '(none provided)'}\n\n"
        f"Candidate resume/profile:\n{ctx.resume or '(none provided)'}"
    )


def get_remaining_seconds(state: InterviewState) -> float:
    """Return seconds left in the interview, or 0 if expired/not started."""
    if state.interview_started_at is None:
        return float(state.interview_duration_minutes * 60)
    elapsed = time.time() - state.interview_started_at
    return max(0.0, state.interview_duration_minutes * 60 - elapsed)


def is_time_expired(state: InterviewState) -> bool:
    """Return True when the interview timer has run out."""
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


def _build_messages(state: InterviewState, instruction: str = "") -> list[dict[str, str]]:
    ctx = state.to_context()
    system_content = get_system_prompt(state.interview_mode) + "\n\n" + _context_block(ctx)
    if instruction:
        system_content += f"\n\nTurn instruction:\n{instruction}"

    messages: list[dict[str, str]] = [{"role": "system", "content": system_content}]
    for msg in state.chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
    return messages


def _call_llm(client: OpenAI, messages: list[dict[str, str]], temperature: float = 0.7) -> str:
    try:
        response = create_chat_completion(
            client,
            model=INTERVIEWLAB_MODEL,
            messages=messages,
            temperature=temperature,
        )
        return (response.choices[0].message.content or "").strip()
    except OpenAIError as exc:
        raise RuntimeError(f"OpenAI request failed: {exc}") from exc


def _parse_json_response(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


def start_interview(state: InterviewState, client: OpenAI) -> str:
    """Begin the interview and return the first interviewer message."""
    reset_interview_state(state)
    state.interview_active = True
    state.interview_started_at = time.time()
    state.total_questions = questions_for_duration(state.interview_duration_minutes)

    instruction = (
        f"This is question 1 of approximately {state.total_questions}. "
        f"The interview is {state.interview_duration_minutes} minutes long. "
        "Welcome the candidate warmly, note this is an English voice mock interview, "
        "and ask the first interview question."
    )
    question = _call_llm(client, _build_messages(state, instruction=instruction), temperature=0.8)

    state.current_question_index = 1
    state.current_question_text = question
    add_message(state, "assistant", question)
    return question


def _check_follow_up(
    client: OpenAI,
    state: InterviewState,
    user_answer: str,
) -> dict[str, Any]:
    ctx = state.to_context()
    user_prompt = (
        f"Mode: {ctx.mode}\n"
        f"Current question: {state.current_question_text}\n"
        f"Candidate answer:\n{user_answer}\n"
        f"Follow-ups already asked for this question: {state.follow_up_count}"
    )
    messages = [
        {"role": "system", "content": FOLLOW_UP_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    raw = _call_llm(client, messages, temperature=0.3)
    try:
        return _parse_json_response(raw)
    except json.JSONDecodeError:
        return {"needs_follow_up": False, "reason": "parse_error", "follow_up_question": ""}


def _generate_next_main_question(state: InterviewState, client: OpenAI) -> str:
    next_index = state.current_question_index + 1
    is_final = next_index >= state.total_questions

    if is_final:
        instruction = (
            f"This is the final main question ({state.total_questions} of "
            f"{state.total_questions}). Explicitly state it is the last question."
        )
    else:
        instruction = (
            f"This is question {next_index} of {state.total_questions}. "
            "Ask the next distinct interview question."
        )

    question = _call_llm(client, _build_messages(state, instruction=instruction), temperature=0.8)

    state.current_question_index = next_index
    state.current_question_text = question
    state.awaiting_follow_up = False
    state.follow_up_count = 0
    add_message(state, "assistant", question)
    return question


def _close_interview(
    state: InterviewState,
    client: OpenAI,
    *,
    time_expired: bool = False,
) -> str:
    if time_expired:
        instruction = (
            "The interview time has expired. "
            "Thank the candidate professionally and clearly state that the interview has concluded."
        )
    else:
        instruction = (
            "The candidate has finished the final question. "
            "Thank them professionally and clearly state that the interview has concluded."
        )
    closing = _call_llm(client, _build_messages(state, instruction=instruction), temperature=0.6)

    state.interview_active = False
    state.interview_complete = True
    add_message(state, "assistant", closing)
    return closing


def force_close_interview(state: InterviewState, client: OpenAI) -> str:
    """Close the interview immediately when the timer expires with no pending answer."""
    return _close_interview(state, client, time_expired=True)


def process_user_response(
    state: InterviewState,
    client: OpenAI,
    user_answer: str,
) -> dict[str, Any]:
    """Handle one candidate turn: follow-up, next question, or close."""
    user_answer = user_answer.strip()
    if not user_answer:
        raise ValueError("Please provide an answer before submitting.")

    add_message(state, "user", user_answer)

    if not is_english_text(user_answer):
        reminder = NON_ENGLISH_INTERVIEWER_REMINDER
        add_message(state, "assistant", reminder)
        return {
            "action": "language_reminder",
            "message": reminder,
            "user_answer": user_answer,
        }

    state.responses.append(
        {
            "question": state.current_question_text,
            "answer": user_answer,
            "question_index": state.current_question_index,
            "is_follow_up": state.awaiting_follow_up,
        }
    )

    if is_time_expired(state):
        closing = _close_interview(state, client, time_expired=True)
        return {
            "action": "complete",
            "message": closing,
            "user_answer": user_answer,
        }

    if state.follow_up_count < 2 and not is_time_expired(state):
        follow_up_check = _check_follow_up(client, state, user_answer)
        if follow_up_check.get("needs_follow_up") and follow_up_check.get("follow_up_question"):
            follow_up_q = follow_up_check["follow_up_question"].strip()
            state.awaiting_follow_up = True
            state.follow_up_count += 1
            state.current_question_text = follow_up_q
            add_message(state, "assistant", follow_up_q)
            return {
                "action": "follow_up",
                "message": follow_up_q,
                "user_answer": user_answer,
            }

    state.awaiting_follow_up = False
    state.follow_up_count = 0

    if state.current_question_index >= state.total_questions or is_time_expired(state):
        closing = _close_interview(state, client)
        return {
            "action": "complete",
            "message": closing,
            "user_answer": user_answer,
        }

    next_q = _generate_next_main_question(state, client)
    return {
        "action": "next_question",
        "message": next_q,
        "user_answer": user_answer,
    }


def get_progress_fraction(state: InterviewState) -> float:
    """Return 0.0–1.0 progress based on time elapsed."""
    if state.interview_complete:
        return 1.0
    if state.interview_started_at is not None:
        return get_time_progress(state)
    if state.total_questions <= 0:
        return 0.0
    completed = max(0, state.current_question_index - 1)
    if state.interview_active and state.responses:
        completed = min(state.current_question_index, state.total_questions)
    return min(completed / state.total_questions, 1.0)
