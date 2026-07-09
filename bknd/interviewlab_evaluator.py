"""
Post-interview and per-turn evaluation logic.

Uses the configured chat model with structured JSON output to score responses
against mode-specific rubrics.
"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI, OpenAIError

from bknd.interviewlab_engine import InterviewState
from bknd.interviewlab_openai import create_chat_completion
from interviewlab_config import INTERVIEWLAB_MODEL, get_rubric


EVALUATION_SYSTEM_PROMPT = """You are an expert interview coach evaluating mock interview performance.

Analyze the full interview transcript and/or the latest Q&A pair.
Apply the provided rubric strictly and respond with JSON only — no markdown.

Required JSON schema:
{
  "overall_score": <integer 0-100>,
  "dimension_scores": {
    "communication_clarity": <integer 1-10>,
    "technical_logical_accuracy": <integer 1-10>,
    "structure": <integer 1-10>
  },
  "strengths": ["string", ...],
  "improvements": ["string", ...],
  "sample_answer": "string — optimized answer for the most recent main question"
}
"""


def _parse_evaluation_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    data = json.loads(text)

    dimension_scores = data.get("dimension_scores", {})
    return {
        "overall_score": int(data.get("overall_score", 0)),
        "dimension_scores": {
            "communication_clarity": int(
                dimension_scores.get("communication_clarity", 0)
            ),
            "technical_logical_accuracy": int(
                dimension_scores.get("technical_logical_accuracy", 0)
            ),
            "structure": int(dimension_scores.get("structure", 0)),
        },
        "strengths": list(data.get("strengths", [])),
        "improvements": list(data.get("improvements", [])),
        "sample_answer": str(data.get("sample_answer", "")),
    }


def _format_transcript(state: InterviewState) -> str:
    if not state.responses:
        return "(No responses recorded.)"

    lines = []
    for i, item in enumerate(state.responses, start=1):
        q_label = "Follow-up" if item.get("is_follow_up") else f"Q{item.get('question_index', i)}"
        lines.append(f"[{q_label}] Interviewer: {item.get('question', '')}")
        lines.append(f"Candidate: {item.get('answer', '')}")
        lines.append("")
    return "\n".join(lines)


def _call_evaluation_llm(
    client: OpenAI,
    mode: str,
    user_content: str,
) -> dict[str, Any]:
    rubric = get_rubric(mode)
    messages = [
        {"role": "system", "content": EVALUATION_SYSTEM_PROMPT + "\n\nRubric:\n" + rubric},
        {"role": "user", "content": user_content},
    ]
    try:
        response = create_chat_completion(
            client,
            model=INTERVIEWLAB_MODEL,
            messages=messages,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "").strip()
        return _parse_evaluation_json(raw)
    except OpenAIError as exc:
        raise RuntimeError(f"Evaluation request failed: {exc}") from exc
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise RuntimeError(f"Could not parse evaluation response: {exc}") from exc


def evaluate_turn(
    client: OpenAI,
    state: InterviewState,
    latest_question: str,
    latest_answer: str,
) -> dict[str, Any]:
    ctx = state.to_context()
    user_content = (
        f"Mode: {ctx.mode}\n"
        f"Job details:\n{ctx.job_description or '(none)'}\n\n"
        f"Latest question:\n{latest_question}\n\n"
        f"Latest answer:\n{latest_answer}\n\n"
        f"Prior transcript:\n{_format_transcript(state)}"
    )
    return _call_evaluation_llm(client, ctx.mode, user_content)


def evaluate_full_interview(
    client: OpenAI,
    state: InterviewState,
) -> dict[str, Any]:
    ctx = state.to_context()
    user_content = (
        f"Mode: {ctx.mode}\n"
        f"Job details:\n{ctx.job_description or '(none)'}\n\n"
        f"Resume:\n{ctx.resume or '(none)'}\n\n"
        f"Full interview transcript:\n{_format_transcript(state)}"
    )
    return _call_evaluation_llm(client, ctx.mode, user_content)


def run_evaluation(
    client: OpenAI,
    state: InterviewState,
    *,
    per_turn: bool = False,
    latest_question: str | None = None,
    latest_answer: str | None = None,
) -> dict[str, Any]:
    if per_turn and latest_question and latest_answer:
        result = evaluate_turn(client, state, latest_question, latest_answer)
        state.turn_evaluations.append(result)
        return result

    result = evaluate_full_interview(client, state)
    state.evaluation_results = result
    state.scores = result
    return result


def get_dimension_labels(mode: str) -> dict[str, str]:
    structure_label = "STAR Structure" if mode == "Behavioral" else "Answer Structure"
    return {
        "communication_clarity": "Communication Clarity",
        "technical_logical_accuracy": "Technical / Logical Accuracy",
        "structure": structure_label,
    }
