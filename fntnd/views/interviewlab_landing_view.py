"""Modern setup / onboarding view on the main page."""

from __future__ import annotations

from collections.abc import Callable

import streamlit as st

_MODE_OPTIONS = [
    (
        "Behavioral",
        "mode_behavioral",
        "💬",
        "Practice STAR stories, teamwork, and leadership scenarios.",
    ),
    (
        "Technical",
        "mode_technical",
        "⚙️",
        "System design, coding concepts, and deep problem solving.",
    ),
]

_DURATION_OPTIONS = [
    (15, "dur_15", "Quick warm-up — a light, easy mock interview to get started."),
    (20, "dur_20", "Balanced practice — realistic pacing with solid depth."),
    (30, "dur_30", "In-depth session — more detailed questions and follow-ups."),
    (45, "dur_45", "Full simulation — the most thorough, mastery-level mock interview."),
]

_INPUT_OPTIONS = [
    (
        "Audio + Text",
        "input_audio_text",
        "🎙️",
        "Speak your answers naturally, like a real interview. Text fallback included.",
    ),
    (
        "Text Only",
        "input_text_only",
        "⌨️",
        "Type your responses — ideal for quiet spaces or focused practice.",
    ),
]


def _section_title(title: str, subtitle: str = "") -> None:
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def _option_card_label(icon: str, title: str, description: str) -> str:
    if icon:
        return f"{icon}\n\n{title}\n{description}"
    return f"{title}\n{description}"


def _render_option_card(
    *,
    button_key: str,
    icon: str,
    title: str,
    description: str,
    is_active: bool,
    on_click: Callable[[], None],
) -> None:
    if st.button(
        _option_card_label(icon, title, description),
        key=button_key,
        use_container_width=True,
        type="primary" if is_active else "secondary",
    ):
        on_click()
        st.rerun()


def _render_hero() -> None:
    st.markdown(
        """
        <div class="hero-section">
            <div class="hero-badge">AI-Powered Practice</div>
            <h1 class="hero-title">Mock Interview Lab</h1>
            <p class="hero-subtitle">
                Prepare for your next opportunity with a realistic, timed mock interview
                tailored to your target role — behavioral or technical.
            </p>
            <div class="feature-row">
                <div class="feature-item">
                    <div class="feature-icon">🎯</div>
                    <div class="feature-text">Role-specific questions</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">⏱️</div>
                    <div class="feature-text">Timed sessions</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">🎙️</div>
                    <div class="feature-text">Voice or text answers</div>
                </div>
                <div class="feature-item">
                    <div class="feature-icon">📊</div>
                    <div class="feature-text">Instant feedback</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_mode_selector() -> None:
    _section_title(
        "Interview Type",
        "Choose the style of practice that matches your upcoming interview.",
    )

    current_mode = st.session_state.get("interview_mode", "Behavioral")
    col1, col2 = st.columns(2)

    for col, (mode, key, icon, desc) in zip((col1, col2), _MODE_OPTIONS):
        with col:
            _render_option_card(
                button_key=key,
                icon=icon,
                title=mode,
                description=desc,
                is_active=current_mode == mode,
                on_click=lambda m=mode: st.session_state.update(interview_mode=m),
            )


def _render_duration_selector() -> None:
    _section_title(
        "Interview Duration",
        "How long your mock interview will run.",
    )

    current_duration = st.session_state.get("interview_duration_minutes", 20)
    cols = st.columns(len(_DURATION_OPTIONS))

    for col, (duration, key, desc) in zip(cols, _DURATION_OPTIONS):
        with col:
            _render_option_card(
                button_key=key,
                icon="⏱️",
                title=f"{duration} min",
                description=desc,
                is_active=current_duration == duration,
                on_click=lambda d=duration: st.session_state.update(
                    interview_duration_minutes=d
                ),
            )


def _render_input_selector() -> None:
    _section_title(
        "Response Method",
        "How you'd like to answer during the interview.",
    )

    current_input = st.session_state.get("input_mode", "Audio + Text")
    col1, col2 = st.columns(2)

    for col, (mode, key, icon, desc) in zip((col1, col2), _INPUT_OPTIONS):
        with col:
            _render_option_card(
                button_key=key,
                icon=icon,
                title=mode,
                description=desc,
                is_active=current_input == mode,
                on_click=lambda m=mode: st.session_state.update(input_mode=m),
            )


def render_setup_view() -> None:
    """Render the full setup form on the main page."""
    _render_hero()

    with st.container():
        _section_title(
            "Job Details",
            "Paste the job title, level, and description — anything that helps tailor your questions.",
        )
        job_details = st.text_area(
            "Job details",
            value=st.session_state.get("job_description", ""),
            height=140,
            placeholder=(
                "e.g. Senior Software Engineer (Mid-Senior)\n\n"
                "We are looking for a backend engineer experienced in Python, "
                "distributed systems, and cloud infrastructure…"
            ),
            label_visibility="collapsed",
        )
        st.session_state["job_description"] = job_details
        st.session_state["target_role"] = ""
        st.session_state["target_level"] = ""

        st.session_state["resume"] = st.text_area(
            "Your background (optional)",
            value=st.session_state.get("resume", ""),
            height=80,
            placeholder="Paste your resume or a brief summary of your experience…",
        )

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        _render_mode_selector()

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        _render_duration_selector()

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        _render_input_selector()

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        if st.button("Begin Mock Interview →", type="primary", use_container_width=True):
            st.session_state["_start_requested"] = True


def render_landing_view() -> None:
    """Alias for setup view — kept for backward compatibility."""
    render_setup_view()
