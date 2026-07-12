"""
Central configuration constants for InterviewLab.

Single source of truth for model ids, interview caps, system prompts, and
evaluation rubrics. Imported by both ``bknd`` and ``fntnd`` modules.

The OpenAI API key is read from Streamlit secrets — users do not enter it in the UI.
"""

from __future__ import annotations

from typing import Any

# -------------------
# Application metadata
# -------------------

APP_TITLE = "AI Mock Interviewer"

# -------------------
# Model configuration
# -------------------

# Post-interview evaluation (and any non-realtime text tasks).
INTERVIEWLAB_MODEL = "gpt-5-mini"

# Live mock interview — OpenAI Realtime voice agent (WebRTC).
# The Realtime model speaks natively (no separate TTS model).
REALTIME_MODEL = "gpt-realtime-2.1-mini"
REALTIME_VOICE = "alloy"
# Transcribes the candidate's mic audio into text for the transcript/eval bridge.
# Interviewer captions come from Realtime output_audio_transcript events (same live session).
REALTIME_TRANSCRIPTION_MODEL = "gpt-4o-mini-transcribe"
# Silence before the interviewer treats your answer as finished (server VAD).
REALTIME_SILENCE_DURATION_MS = 5000
# If True, any mic noise barges in and cuts off the interviewer mid-question.
REALTIME_INTERRUPT_RESPONSE = False
# Server VAD sensitivity (0–1). Higher = less likely to treat background noise as speech.
REALTIME_VAD_THRESHOLD = 0.65
REALTIME_VAD_PREFIX_PADDING_MS = 300

# -------------------
# Voice security / anti-prompt-hacking
# -------------------

# Consecutive blocked misuse turns before the live session is force-ended.
SECURITY_MAX_CONSECUTIVE_STRIKES = 3

# -------------------
# Interview settings
# -------------------

# Fallback question count when duration mapping is unavailable.
TOTAL_QUESTIONS = 5

# Interview duration options (minutes).
DURATION_OPTIONS = (15, 20, 30, 45)
DEFAULT_DURATION_MINUTES = 20

# Approximate minutes per main question — used to derive question count from duration.
MINUTES_PER_QUESTION = 4

INTERVIEW_MODES = ("Behavioral", "Technical")

# Voice-only spoken interviews (English).
SUPPORTED_INTERVIEW_LANGUAGE = "English"

# Default session keys — mirrored by ``fntnd.interviewlab_state.init_session_state``.
SESSION_DEFAULTS: dict[str, Any] = {
    "interview_active": False,
    "interview_complete": False,
    "interview_mode": "Behavioral",
    "target_role": "",
    "target_level": "",
    "job_description": "",
    "resume": "",
    "resume_typed": "",
    "resume_file_text": "",
    "resume_file_name": "",
    "resume_file_hash": None,
    "chat_history": [],
    "current_question_index": 0,
    "total_questions": TOTAL_QUESTIONS,
    "current_question_text": "",
    "responses": [],
    "awaiting_follow_up": False,
    "follow_up_count": 0,
    "scores": None,
    "evaluation_results": None,
    "turn_evaluations": [],
    "error_message": None,
    "interview_duration_minutes": DEFAULT_DURATION_MINUTES,
    "interview_started_at": None,
    "interview_session_started": False,
    "live_caption_text": None,
    "live_caption_speaker": None,
    "active_speaker": None,
    "interview_phase": "connecting",
    "realtime_ephemeral_key": None,
    "realtime_session_id": 0,
    "realtime_transcript": [],
    "last_realtime_payload": None,
    "_disconnect_realtime": False,
    "_time_expired": False,
    "_show_end_interview_confirm": False,
    "_generating_interview": False,
    "_generating_worker_started": False,
    "security_consecutive_strikes": 0,
    "security_terminated": False,
    "_security_notice": None,
}

# -------------------
# System prompts
# -------------------

ENGLISH_ONLY_RULE = """
Language (required):
- Conduct this mock interview entirely in English.
- The candidate is practicing for English-language job interviews.
- If the candidate responds in another language, politely remind them to answer in English and repeat your last question without advancing.
"""

BEHAVIORAL_SYSTEM_PROMPT = """You are an experienced HR Manager conducting a realistic behavioral mock interview in English.

Your goals:
1. Ask one short, direct behavioral question at a time — exactly like a real interviewer would.
2. Tailor questions to BOTH the job details and the candidate's background/resume when provided.
3. Keep questions to 1–2 sentences. No bullet lists, no coaching, no methodology explanations.
4. If an answer is vague or incomplete, ask a brief natural follow-up (e.g. "What was the result?" or "What did you personally do?").
5. Be professional, warm, and concise. Do not lecture.
6. On the first turn: one brief welcome sentence, then your first question.
7. Pace questions naturally for the allotted interview duration.
8. On the final main question, you may briefly note it is the last question.
9. After the final answer, thank the candidate and state the interview has concluded.

Rules:
- Ask only ONE question or follow-up per turn.
- NEVER mention STAR, Situation/Task/Action/Result, or how to structure answers in your questions.
- NEVER tell the candidate what to include in their answer (no "include X, Y, Z").
- Answer-structure coaching belongs in post-interview feedback only — not during the live interview.
- Do not reveal scoring criteria during the interview.
""" + ENGLISH_ONLY_RULE

TECHNICAL_SYSTEM_PROMPT = """You are a Technical Lead conducting a realistic technical mock interview in English.

Your goals:
1. Ask one short, direct technical question at a time — exactly like a real interviewer would.
2. Tailor questions to BOTH the job details and the candidate's background/resume when provided.
3. Keep questions to 1–2 sentences. No bullet lists, no coaching, no hints about how to answer.
4. If an answer is shallow or unclear, ask a brief natural follow-up probe.
5. Be professional and concise. Do not give away solutions during the interview.
6. On the first turn: one brief welcome sentence, then your first question.
7. Pace questions naturally for the allotted interview duration.
8. On the final main question, you may briefly note it is the last question.
9. After the final answer, thank the candidate and state the interview has concluded.

Rules:
- Ask only ONE question or follow-up per turn.
- NEVER explain frameworks, formats, or what the candidate should cover in their answer.
- Do not reveal scoring criteria during the interview.
- Scale difficulty to the stated level (Junior / Mid / Senior).
""" + ENGLISH_ONLY_RULE

# -------------------
# Evaluation rubrics
# -------------------

BEHAVIORAL_RUBRIC = """
Score each dimension from 0-10 based ONLY on spoken candidate answers:

1. Communication Clarity — articulation, concision, professional tone.
2. Technical/Logical Accuracy — relevance of examples to the role; logical reasoning in stories.
3. Structure (STAR) — completeness and clarity of Situation, Task, Action, Result.

If there are no candidate answers, all dimension scores and overall_score must be 0.

Also provide:
- overall_score: integer 0-100 (weighted average mapped to 100-point scale)
- strengths: list of 2-4 bullet strings about what the candidate said ("What went well")
- improvements: list of 2-4 bullet strings ("Areas for improvement")
- sample_answer: a polished example answer for the most recent question (empty string if none)
"""

TECHNICAL_RUBRIC = """
Score each dimension from 0-10 based ONLY on spoken candidate answers:

1. Communication Clarity — ability to explain technical concepts clearly.
2. Technical/Logical Accuracy — correctness, depth, and role-appropriate knowledge.
3. Structure — organized reasoning, trade-off discussion, step-by-step clarity.

If there are no candidate answers, all dimension scores and overall_score must be 0.

Also provide:
- overall_score: integer 0-100
- strengths: list of 2-4 bullet strings about what the candidate said
- improvements: list of 2-4 bullet strings
- sample_answer: an optimized answer to the most recent question (empty string if none)
"""


def get_system_prompt(mode: str) -> str:
    """Return the interviewer system prompt for the selected mode."""
    if mode == "Technical":
        return TECHNICAL_SYSTEM_PROMPT
    return BEHAVIORAL_SYSTEM_PROMPT


def get_rubric(mode: str) -> str:
    """Return the evaluation rubric for the selected mode."""
    if mode == "Technical":
        return TECHNICAL_RUBRIC
    return BEHAVIORAL_RUBRIC


def questions_for_duration(minutes: int) -> int:
    """Derive a reasonable question count from interview duration."""
    return max(3, min(8, round(minutes / MINUTES_PER_QUESTION)))
