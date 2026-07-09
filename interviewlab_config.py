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

# Primary chat model for interview dialogue and evaluation.
INTERVIEWLAB_MODEL = "gpt-5-mini"

# Speech-to-text (primary + fallback for accounts without the latest audio models).
WHISPER_MODEL = "gpt-4o-transcribe"
WHISPER_FALLBACK_MODEL = "whisper-1"

# Text-to-speech for optional AI voice responses.
TTS_MODEL = "gpt-4o-mini-tts"
TTS_FALLBACK_MODEL = "tts-1"
TTS_VOICE = "alloy"

# -------------------
# Interview settings
# -------------------

TOTAL_QUESTIONS = 5

# Interview duration options (minutes).
DURATION_OPTIONS = (15, 20, 30, 45)
DEFAULT_DURATION_MINUTES = 20

# Approximate minutes per main question — used to derive question count from duration.
MINUTES_PER_QUESTION = 4

# When True, evaluation runs after each answer; when False, only at the end.
PER_TURN_EVALUATION = False

INTERVIEW_MODES = ("Behavioral", "Technical")

# Voice-only spoken interviews (English).
SUPPORTED_INTERVIEW_LANGUAGE = "English"

# Auto-submit the candidate's answer after this many seconds of silence.
ANSWER_COOLDOWN_SECONDS = 15
SILENCE_SUBMIT_SECONDS = ANSWER_COOLDOWN_SECONDS

# Default session keys — mirrored by ``fntnd.interviewlab_state.init_session_state``.
SESSION_DEFAULTS: dict[str, Any] = {
    "openai_api_key": "",
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
    "ai_voice_enabled": True,
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
    "last_tts_audio": None,
    "error_message": None,
    "interview_duration_minutes": DEFAULT_DURATION_MINUTES,
    "interview_started_at": None,
    "interview_session_started": False,
    "setup_complete": False,
    "last_audio_hash": None,
    "live_caption_text": None,
    "live_caption_speaker": None,
    "live_caption_expires_at": None,
    "active_speaker": None,
    "interview_phase": "listening",
    "pending_answer_audio": None,
    "pending_answer_text": None,
    "next_question_at": None,
    "_auto_start_session": False,
    "mic_turn_id": 0,
    "mic_auto_start": False,
    "_stop_mic_now": False,
    "last_mic_payload": None,
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

FOLLOW_UP_SYSTEM_PROMPT = """You are reviewing the candidate's latest answer during an English-only mock interview.

Determine whether a brief follow-up is needed:
- Behavioral mode: check if the answer lacks concrete detail, personal ownership, or a clear outcome. If so, ask ONE short natural follow-up (e.g. "What was the measurable result?" or "What was your specific role?"). Do NOT mention STAR or answer frameworks.
- Technical mode: check depth and accuracy. If shallow, ask ONE short clarifying or probing question.

Respond in JSON only with this schema:
{
  "needs_follow_up": true or false,
  "reason": "brief explanation",
  "follow_up_question": "one short follow-up question if needs_follow_up is true, else empty string"
}
"""

# -------------------
# Evaluation rubrics
# -------------------

BEHAVIORAL_RUBRIC = """
Score each dimension from 1-10:

1. Communication Clarity — articulation, concision, professional tone.
2. Technical/Logical Accuracy — relevance of examples to the role; logical reasoning in stories.
3. Structure (STAR) — completeness and clarity of Situation, Task, Action, Result.

Also provide:
- overall_score: integer 0-100 (weighted average mapped to 100-point scale)
- strengths: list of 2-4 bullet strings ("What went well")
- improvements: list of 2-4 bullet strings ("Areas for improvement")
- sample_answer: a polished example answer for the most recent question
"""

TECHNICAL_RUBRIC = """
Score each dimension from 1-10:

1. Communication Clarity — ability to explain technical concepts clearly.
2. Technical/Logical Accuracy — correctness, depth, and role-appropriate knowledge.
3. Structure — organized reasoning, trade-off discussion, step-by-step clarity.

Also provide:
- overall_score: integer 0-100
- strengths: list of 2-4 bullet strings
- improvements: list of 2-4 bullet strings
- sample_answer: an optimized answer to the most recent question
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
