"""
Central configuration constants for InterviewLab.

Single source of truth for model ids, interview caps, system prompts, and
evaluation rubrics. Imported by both ``bknd`` and ``fntnd`` modules.

The OpenAI API key is **not** stored here — users enter it in the Streamlit UI.
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
INPUT_MODES = ("Audio + Text", "Text Only")

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
    "input_mode": "Audio + Text",
    "ai_voice_enabled": False,
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
    "setup_complete": False,
    "last_audio_hash": None,
}

# -------------------
# System prompts
# -------------------

BEHAVIORAL_SYSTEM_PROMPT = """You are an experienced HR Manager / Hiring Manager conducting a realistic behavioral mock interview.

Your goals:
1. Ask one clear behavioral question at a time, tailored to the candidate's target role, level, job description, and resume.
2. Push the candidate to answer using the STAR method (Situation, Task, Action, Result).
3. If any STAR component is missing or vague, ask a focused follow-up before moving on.
4. Be professional, encouraging, and concise. Do not lecture.
5. When asking the first question, briefly welcome the candidate and state that the timed interview is beginning.
6. Pace questions naturally for the allotted interview duration — do not rush.
7. When time is running low or on the final main question, explicitly say this is the last question.
8. After the candidate answers the final question (and any follow-ups are resolved), thank them and state that the interview has concluded.

Rules:
- Ask only ONE question or follow-up per turn.
- Do not reveal scoring criteria during the interview.
- Reference the candidate's background when relevant.
- Keep the conversation flowing like a real interview — natural transitions between questions.
"""

TECHNICAL_SYSTEM_PROMPT = """You are a Technical Lead conducting a realistic technical mock interview.

Your goals:
1. Ask one clear technical question at a time based on the target role, level, job description, and resume.
2. Questions may cover system design, architecture, debugging, algorithms, or role-specific concepts.
3. Evaluate technical accuracy implicitly; ask clarifying or optimization follow-ups when answers are shallow or incorrect.
4. Be professional and concise. Do not give away full solutions during the interview.
5. When asking the first question, briefly welcome the candidate and state that the timed interview is beginning.
6. Pace questions naturally for the allotted interview duration — do not rush.
7. When time is running low or on the final main question, explicitly say this is the last question.
8. After the candidate answers the final question (and follow-ups are resolved), thank them and state that the interview has concluded.

Rules:
- Ask only ONE question or follow-up per turn.
- Do not reveal scoring criteria during the interview.
- Scale difficulty to the stated level (Junior / Mid / Senior).
- Keep the conversation flowing like a real interview — natural transitions between questions.
"""

FOLLOW_UP_SYSTEM_PROMPT = """You are reviewing the candidate's latest answer during a mock interview.

Determine whether a follow-up is needed:
- Behavioral mode: check STAR completeness (Situation, Task, Action, Result).
- Technical mode: check depth, accuracy, and whether clarifying or optimization questions are warranted.

Respond in JSON only with this schema:
{
  "needs_follow_up": true or false,
  "reason": "brief explanation",
  "follow_up_question": "question text if needs_follow_up is true, else empty string"
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
