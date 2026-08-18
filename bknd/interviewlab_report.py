"""Markdown and PDF report builders for a completed mock interview."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from bknd.interviewlab_evaluator import get_dimension_labels
from interviewlab_config import get_rubric


def _safe_filename_part(text: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "-", (text or "").strip(), flags=re.UNICODE)
    cleaned = cleaned.strip("-") or "interview"
    return cleaned[:40]


def report_filename(payload: dict[str, Any], ext: str) -> str:
    """Return a download filename like InterviewLab-Behavioral-72-2026-08-17.md."""
    mode = _safe_filename_part(str(payload.get("mode") or "interview"))
    score = int(payload.get("overall_score") or 0)
    raw_when = str(payload.get("completed_at") or "")
    try:
        day = datetime.fromisoformat(raw_when.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        day = datetime.now(timezone.utc).date().isoformat()
    suffix = ext.lstrip(".")
    return f"InterviewLab-{mode}-{score}-{day}.{suffix}"


def _format_completed_at(payload: dict[str, Any]) -> str:
    raw = str(payload.get("completed_at") or "").strip()
    if not raw:
        return "—"
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except ValueError:
        return raw


def _bullet_block(items: list[Any], empty: str) -> str:
    lines = [f"- {str(item).strip()}" for item in items if str(item).strip()]
    return "\n".join(lines) if lines else f"- {empty}"


def build_markdown_report(payload: dict[str, Any]) -> str:
    """Render a full interview report as Markdown."""
    mode = str(payload.get("mode") or "Behavioral")
    labels = get_dimension_labels(mode)
    dims = payload.get("dimension_scores") or {}
    rubric = (get_rubric(mode) or "").strip()
    lines: list[str] = [
        "# InterviewLab Report",
        "",
        f"- **Date:** {_format_completed_at(payload)}",
        f"- **Mode:** {mode}",
        f"- **Role:** {payload.get('role_label') or 'Mock Interview'}",
        f"- **Duration:** {int(payload.get('duration_minutes') or 0)} minutes",
        f"- **Responses scored:** {int(payload.get('answer_count') or 0)}",
        f"- **Overall score:** {int(payload.get('overall_score') or 0)} / 100",
    ]
    if payload.get("security_terminated"):
        lines.append("- **Status:** Session ended for misuse")
    lines.extend(["", "## Rubric", "", rubric or "(No rubric text.)", "", "## Dimension scores", ""])
    for key, label in labels.items():
        lines.append(f"- **{label}:** {int(dims.get(key) or 0)} / 10")
    lines.extend(
        [
            "",
            "## What went well",
            "",
            _bullet_block(list(payload.get("strengths") or []), "None recorded."),
            "",
            "## Areas to improve",
            "",
            _bullet_block(list(payload.get("improvements") or []), "None recorded."),
        ]
    )
    sample = str(payload.get("sample_answer") or "").strip()
    if sample:
        lines.extend(["", "## Sample optimized answer", "", sample])

    turns = list(payload.get("turn_evaluations") or [])
    if turns:
        lines.extend(["", "## Per-question scores", ""])
        for i, turn in enumerate(turns, start=1):
            kind = "Follow-up" if turn.get("is_follow_up") else f"Q{turn.get('question_index') or i}"
            score = turn.get("overall_score", "—")
            scored = turn.get("scored", True)
            lines.append(f"### {kind} — {score}/100" if scored else f"### {kind} — score unavailable")
            lines.append("")
            lines.append(f"**Interviewer:** {turn.get('question') or ''}")
            lines.append("")
            lines.append(f"**You:** {turn.get('answer') or ''}")
            lines.append("")
            if scored:
                tdims = turn.get("dimension_scores") or {}
                dim_bits = [
                    f"{labels[key]} {int(tdims.get(key) or 0)}/10"
                    for key in labels
                ]
                lines.append("Dimensions: " + " · ".join(dim_bits))
                lines.append("")
            feedback = str(turn.get("feedback") or "").strip()
            if feedback:
                lines.append(feedback)
                lines.append("")

    lines.extend(["", "## Transcript", ""])
    transcript = list(payload.get("chat_history") or [])
    if not transcript:
        lines.append("_No transcript recorded._")
    else:
        for msg in transcript:
            speaker = "Interviewer" if msg.get("role") == "assistant" else "You"
            content = (msg.get("content") or "").strip()
            if content:
                lines.append(f"**{speaker}:** {content}")
                lines.append("")
    return "\n".join(lines).strip() + "\n"


def _pdf_safe(text: str) -> str:
    """Helvetica core fonts are Latin-1; replace unsupported glyphs."""
    return (text or "").encode("latin-1", "replace").decode("latin-1")


def build_pdf_report(payload: dict[str, Any]) -> bytes:
    """Render the same report as a simple PDF (English-oriented Latin-1)."""
    from fpdf import FPDF

    mode = str(payload.get("mode") or "Behavioral")
    labels = get_dimension_labels(mode)
    dims = payload.get("dimension_scores") or {}
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_page()

    def write_line(text: str, *, height: float = 6) -> None:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(
            pdf.epw,
            height,
            _pdf_safe(text),
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.set_font("Helvetica", "B", 18)
    write_line("InterviewLab Report", height=10)
    pdf.set_font("Helvetica", "", 11)
    meta = [
        f"Date: {_format_completed_at(payload)}",
        f"Mode: {mode}",
        f"Role: {payload.get('role_label') or 'Mock Interview'}",
        f"Duration: {int(payload.get('duration_minutes') or 0)} minutes",
        f"Responses scored: {int(payload.get('answer_count') or 0)}",
        f"Overall score: {int(payload.get('overall_score') or 0)} / 100",
    ]
    if payload.get("security_terminated"):
        meta.append("Status: Session ended for misuse")
    write_line("\n".join(meta))
    pdf.ln(3)

    def heading(title: str) -> None:
        pdf.set_font("Helvetica", "B", 13)
        write_line(title, height=8)
        pdf.set_font("Helvetica", "", 11)

    heading("Rubric")
    write_line((get_rubric(mode) or "").strip() or "(No rubric text.)", height=5)
    pdf.ln(2)
    heading("Dimension scores")
    for key, label in labels.items():
        write_line(f"- {label}: {int(dims.get(key) or 0)} / 10")
    pdf.ln(2)
    heading("What went well")
    strengths = [str(s) for s in (payload.get("strengths") or []) if str(s).strip()]
    write_line("\n".join(f"- {s}" for s in strengths) or "- None recorded.")
    pdf.ln(2)
    heading("Areas to improve")
    improvements = [str(s) for s in (payload.get("improvements") or []) if str(s).strip()]
    write_line("\n".join(f"- {s}" for s in improvements) or "- None recorded.")
    sample = str(payload.get("sample_answer") or "").strip()
    if sample:
        pdf.ln(2)
        heading("Sample optimized answer")
        write_line(sample)

    turns = list(payload.get("turn_evaluations") or [])
    if turns:
        pdf.ln(2)
        heading("Per-question scores")
        for i, turn in enumerate(turns, start=1):
            kind = "Follow-up" if turn.get("is_follow_up") else f"Q{turn.get('question_index') or i}"
            scored = turn.get("scored", True)
            title = f"{kind} — {turn.get('overall_score', '—')}/100" if scored else f"{kind} — score unavailable"
            pdf.set_font("Helvetica", "B", 11)
            write_line(title)
            pdf.set_font("Helvetica", "", 11)
            write_line(f"Interviewer: {turn.get('question') or ''}", height=5)
            write_line(f"You: {turn.get('answer') or ''}", height=5)
            if scored:
                tdims = turn.get("dimension_scores") or {}
                dim_line = " · ".join(
                    f"{labels[key]} {int(tdims.get(key) or 0)}/10" for key in labels
                )
                write_line(dim_line, height=5)
            feedback = str(turn.get("feedback") or "").strip()
            if feedback:
                write_line(feedback, height=5)
            pdf.ln(1)

    pdf.ln(2)
    heading("Transcript")
    transcript = list(payload.get("chat_history") or [])
    if not transcript:
        write_line("No transcript recorded.")
    else:
        for msg in transcript:
            speaker = "Interviewer" if msg.get("role") == "assistant" else "You"
            content = (msg.get("content") or "").strip()
            if content:
                write_line(f"{speaker}: {content}", height=5)
                pdf.ln(1)

    out = pdf.output()
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return bytes(out)


def payload_from_session(session: dict[str, Any], *, role_label: str) -> dict[str, Any]:
    """Build a report payload from Streamlit-like session keys."""
    results = session.get("evaluation_results") or {}
    return {
        "completed_at": session.get("interview_completed_at")
        or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": session.get("interview_mode") or "Behavioral",
        "role_label": role_label or "Mock Interview",
        "job_description": session.get("job_description") or "",
        "duration_minutes": int(session.get("interview_duration_minutes") or 0),
        "overall_score": int(results.get("overall_score") or 0),
        "dimension_scores": dict(results.get("dimension_scores") or {}),
        "strengths": list(results.get("strengths") or []),
        "improvements": list(results.get("improvements") or []),
        "sample_answer": str(results.get("sample_answer") or ""),
        "turn_evaluations": list(session.get("turn_evaluations") or []),
        "chat_history": list(session.get("chat_history") or []),
        "answer_count": _session_answer_count(session),
        "security_terminated": bool(
            session.get("security_terminated") or results.get("security_terminated")
        ),
    }


def _session_answer_count(session: dict[str, Any]) -> int:
    responses = [
        r
        for r in (session.get("responses") or [])
        if (r.get("answer") or "").strip()
    ]
    if responses:
        return len(responses)
    return sum(
        1
        for m in (session.get("chat_history") or [])
        if m.get("role") == "user" and (m.get("content") or "").strip()
    )
