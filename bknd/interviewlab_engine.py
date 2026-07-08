"""
Interview conversation engine.

Manages state transitions, prompt construction, and LLM calls. Accepts plain
data structures rather than reading ``st.session_state`` directly so storage can
later be swapped for a database without rewriting core logic.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI, OpenAIError

from interviewlab_config import (
    FOLLOW_UP_SYSTEM_PROMPT,
    INTERVIEWLAB_MODEL,
    TOTAL_QUESTIONS,
    get_system_prompt,
)


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
    input_mode: str = "Audio + Text"
    ai_voice_enabled: bool = False
    chat_history: list[dict[str, str]] = field(default_factory=list)
    current_question_index: int = 0
    total_questions: int = TOTAL_QUESTIONS
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


def _context_block(ctx: InterviewContext) -> str:
    return (
        f"Interview mode: {ctx.mode}\n"
        f"Target role: {ctx.target_role or 'Not specified'}\n"
        f"Level: {ctx.target_level or 'Not specified'}\n"
        f"Total main questions: {ctx.total_questions}\n\n"
        f"Job description:\n{ctx.job_description or '(none provided)'}\n\n"
        f"Candidate resume/profile:\n{ctx.resume or '(none provided)'}"
    )


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
        response = client.chat.completions.create(
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
    state.total_questions = TOTAL_QUESTIONS

    instruction = (
        f"This is question 1 of {state.total_questions}. "
        "Welcome the candidate and ask the first interview question."
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


def _close_interview(state: InterviewState, client: OpenAI) -> str:
    instruction = (
        "The candidate has finished the final question. "
        "Thank them professionally and clearly state that the interview has concluded."
    )
    closing = _call_llm(client, _build_messages(state, instruction=instruction), temperature=0.6)

    state.interview_active = False
    state.interview_complete = True
    add_message(state, "assistant", closing)
    return closing


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
    state.responses.append(
        {
            "question": state.current_question_text,
            "answer": user_answer,
            "question_index": state.current_question_index,
            "is_follow_up": state.awaiting_follow_up,
        }
    )

    if state.follow_up_count < 2:
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

    if state.current_question_index >= state.total_questions:
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
    """Return 0.0–1.0 progress for the progress bar."""
    if state.total_questions <= 0:
        return 0.0
    if state.interview_complete:
        return 1.0
    completed = max(0, state.current_question_index - 1)
    if state.interview_active and state.responses:
        completed = min(state.current_question_index, state.total_questions)
    return min(completed / state.total_questions, 1.0)
