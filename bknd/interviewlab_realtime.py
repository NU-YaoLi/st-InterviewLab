"""OpenAI Realtime session helpers for live mock interviews."""

from __future__ import annotations

from typing import Any

import httpx

from bknd.interviewlab_engine import InterviewState, context_block, reset_interview_state
from interviewlab_config import (
    REALTIME_INTERRUPT_RESPONSE,
    REALTIME_MODEL,
    REALTIME_SILENCE_DURATION_MS,
    REALTIME_TRANSCRIPTION_MODEL,
    REALTIME_VAD_PREFIX_PADDING_MS,
    REALTIME_VAD_THRESHOLD,
    REALTIME_VOICE,
    get_system_prompt,
    questions_for_duration,
)
from bknd.interviewlab_security import SECURITY_SYSTEM_RULES


def build_realtime_instructions(state: InterviewState) -> str:
    """Build interviewer instructions for the Realtime voice session."""
    ctx = state.to_context()
    total = questions_for_duration(state.interview_duration_minutes)
    duration = state.interview_duration_minutes

    return (
        get_system_prompt(state.interview_mode)
        + "\n\n"
        + SECURITY_SYSTEM_RULES
        + "\n\n"
        + context_block(ctx)
        + f"\n\nLive session settings:\n"
        f"- Interview duration: about {duration} minutes.\n"
        f"- Aim for approximately {total} main questions, with brief follow-ups when needed.\n"
        "- This is a spoken voice interview. Keep every turn short and natural.\n"
        "- Start immediately with one brief welcome sentence, then your first question.\n"
        "- Wait for the candidate to finish speaking before asking the next question.\n"
        "- After each candidate answer, briefly acknowledge what they said in one short "
        "natural phrase (e.g. \"Thanks, that helps.\" / \"Got it.\"), then either ask ONE "
        "short follow-up when the answer is vague, or move to the next distinct question.\n"
        "- Do not jump to the next question with zero acknowledgment — keep the conversation "
        "interactive and human, like a real interviewer.\n"
        "- Prefer one thoughtful follow-up over rushing through many shallow questions.\n"
        "- When the interview should end (final answer complete, or you are told time is up), "
        "thank the candidate and clearly say that the interview has concluded.\n"
        "- Prefer ending with the exact phrase: \"This interview has concluded.\"\n"
        "- Do not mention that you are an AI model or that this uses a realtime API.\n"
    )


def build_realtime_session_config(state: InterviewState) -> dict[str, Any]:
    """Session payload for POST /v1/realtime/client_secrets."""
    return {
        "session": {
            "type": "realtime",
            "model": REALTIME_MODEL,
            "instructions": build_realtime_instructions(state),
            "audio": {
                "input": {
                    "transcription": {"model": REALTIME_TRANSCRIPTION_MODEL},
                    "turn_detection": {
                        "type": "server_vad",
                        "create_response": True,
                        # Defense-in-depth: client also mutes mic while interviewer speaks.
                        # interrupt_response alone is not enough — mic audio still reaches VAD.
                        "interrupt_response": REALTIME_INTERRUPT_RESPONSE,
                        "silence_duration_ms": REALTIME_SILENCE_DURATION_MS,
                        "prefix_padding_ms": REALTIME_VAD_PREFIX_PADDING_MS,
                        "threshold": REALTIME_VAD_THRESHOLD,
                    },
                },
                "output": {
                    "voice": REALTIME_VOICE,
                },
            },
        }
    }


def create_realtime_client_secret(api_key: str, state: InterviewState) -> str:
    """Mint a short-lived ephemeral key for browser WebRTC. Never expose the root key."""
    key = (api_key or "").strip()
    if not key:
        raise ValueError("Interview service is not configured.")

    payload = build_realtime_session_config(state)
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            "https://api.openai.com/v1/realtime/client_secrets",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )

    if response.status_code >= 400:
        detail = response.text[:500]
        raise RuntimeError(
            f"Failed to create Realtime session ({response.status_code}): {detail}"
        )

    data = response.json()
    ephemeral = data.get("value") or data.get("client_secret", {}).get("value")
    if not ephemeral:
        raise RuntimeError("Realtime client secret response missing value.")
    return str(ephemeral)


def prepare_realtime_interview(state: InterviewState) -> None:
    """Mark interview active and ready for a Realtime WebRTC session."""
    reset_interview_state(state)
    state.interview_active = True
    state.total_questions = questions_for_duration(state.interview_duration_minutes)


def sync_transcript_to_state(
    state: InterviewState,
    transcript: list[dict[str, str]],
) -> None:
    """Map Realtime transcript turns into chat_history and Q/A responses."""
    from bknd.interviewlab_security import filter_transcript_for_evaluation

    safe_transcript = filter_transcript_for_evaluation(transcript)
    state.chat_history = [
        {"role": m["role"], "content": m["content"]}
        for m in safe_transcript
    ]

    responses: list[dict[str, Any]] = []
    pending_question = ""
    pending_is_follow_up = False
    question_index = 0
    just_answered = False
    for msg in state.chat_history:
        if msg["role"] == "assistant":
            content = msg["content"]
            # Heuristic: short probe after a candidate answer is treated as a follow-up.
            pending_is_follow_up = (
                just_answered
                and len(content.split()) <= 28
                and "?" in content
            )
            pending_question = content
            just_answered = False
        elif msg["role"] == "user" and pending_question:
            if not pending_is_follow_up:
                question_index += 1
            responses.append(
                {
                    "question_index": question_index or 1,
                    "question": pending_question,
                    "answer": msg["content"],
                    "is_follow_up": pending_is_follow_up,
                }
            )
            just_answered = True
            pending_question = ""
            pending_is_follow_up = False

    state.responses = responses
    state.current_question_index = question_index
    if pending_question:
        state.current_question_text = pending_question
    elif responses:
        state.current_question_text = responses[-1]["question"]


def finalize_realtime_interview(state: InterviewState) -> None:
    """Close interview flags after the live Realtime session ends."""
    state.interview_active = False
    state.interview_complete = True
    state.interview_session_started = False
