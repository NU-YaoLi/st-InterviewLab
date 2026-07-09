"""Modern setup / onboarding view on the main page."""

from __future__ import annotations

import hashlib

import streamlit as st

from bknd.interviewlab_resume import ResumeParseError, combine_resume_sources, extract_resume_text
from fntnd.interviewlab_errors import show_validation_error

_MODE_OPTIONS = [
    (
        "Behavioral",
        "mode_behavioral",
        "interview_mode",
        "💬",
        "Practice STAR stories, teamwork, and leadership scenarios.",
    ),
    (
        "Technical",
        "mode_technical",
        "interview_mode",
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


def _section_title(title: str, subtitle: str = "") -> None:
    st.markdown(f"#### {title}")
    if subtitle:
        st.caption(subtitle)


def _set_session_value(key: str, value: object) -> None:
    if st.session_state.get(key) != value:
        st.session_state[key] = value


def _sync_resume_from_sources(typed_background: str, uploaded_resume) -> None:
    """Parse uploaded resume if needed and store the combined background text."""
    uploaded_text = st.session_state.get("resume_file_text", "")
    uploaded_name = st.session_state.get("resume_file_name", "")

    if uploaded_resume is not None:
        file_bytes = uploaded_resume.getvalue()
        file_hash = hashlib.md5(file_bytes).hexdigest()
        if file_hash != st.session_state.get("resume_file_hash"):
            try:
                uploaded_text = extract_resume_text(uploaded_resume)
                st.session_state["resume_file_text"] = uploaded_text
                st.session_state["resume_file_name"] = uploaded_resume.name
                st.session_state["resume_file_hash"] = file_hash
                uploaded_name = uploaded_resume.name
                st.success(f"Resume uploaded: {uploaded_resume.name}")
            except ResumeParseError as exc:
                st.error(str(exc))
                return
    elif st.session_state.get("resume_file_hash") is not None:
        uploaded_text = ""
        uploaded_name = ""
        st.session_state["resume_file_text"] = ""
        st.session_state["resume_file_name"] = ""
        st.session_state["resume_file_hash"] = None

    st.session_state["resume"] = combine_resume_sources(
        typed_text=typed_background,
        uploaded_text=uploaded_text,
        uploaded_name=uploaded_name,
    )


def _option_card_label(icon: str, title: str, description: str) -> str:
    if icon:
        return f"{icon}\n\n{title}\n{description}"
    return f"{title}\n{description}"


def _inject_active_card_style(active_button_key: str) -> None:
    st.markdown(
        f"""
        <style>
        .st-key-{active_button_key} button {{
            background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%) !important;
            border: 2px solid #6366f1 !important;
            box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_option_card(
    *,
    button_key: str,
    session_key: str,
    session_value: object,
    icon: str,
    title: str,
    description: str,
) -> None:
    st.button(
        _option_card_label(icon, title, description),
        key=button_key,
        use_container_width=True,
        type="secondary",
        on_click=_set_session_value,
        kwargs={"key": session_key, "value": session_value},
    )


def _render_hero() -> None:
    st.markdown(
        """
        <div class="hero-section">
            <div class="hero-badge">AI-Powered Practice</div>
            <h1 class="hero-title">Mock Interview Lab</h1>
            <div class="hero-subtitle-wrap">
                <p class="hero-subtitle">
                    Prepare for your next opportunity with a realistic, timed mock interview
                    tailored to your target role — behavioral or technical.
                </p>
            </div>
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
                    <div class="feature-text">English voice practice</div>
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


@st.fragment
def _mode_selector_fragment() -> None:
    _section_title(
        "Interview Type",
        "Choose the style of practice that matches your upcoming interview.",
    )

    current_mode = st.session_state.get("interview_mode", "Behavioral")
    active_key = f"mode_{current_mode.lower()}"
    _inject_active_card_style(active_key)

    col1, col2 = st.columns(2)
    for col, (mode, key, session_key, icon, desc) in zip((col1, col2), _MODE_OPTIONS):
        with col:
            _render_option_card(
                button_key=key,
                session_key=session_key,
                session_value=mode,
                icon=icon,
                title=mode,
                description=desc,
            )


@st.fragment
def _duration_selector_fragment() -> None:
    _section_title(
        "Interview Duration",
        "How long your mock interview will run.",
    )

    current_duration = st.session_state.get("interview_duration_minutes", 20)
    _inject_active_card_style(f"dur_{current_duration}")

    cols = st.columns(len(_DURATION_OPTIONS))
    for col, (duration, key, desc) in zip(cols, _DURATION_OPTIONS):
        with col:
            _render_option_card(
                button_key=key,
                session_key="interview_duration_minutes",
                session_value=duration,
                icon="⏱️",
                title=f"{duration} min",
                description=desc,
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

        _section_title(
            "Your Background",
            "Paste notes or upload your resume — questions will be tailored to your experience and the job.",
        )

        typed_background = st.text_area(
            "Background notes",
            value=st.session_state.get("resume_typed", st.session_state.get("resume", "")),
            height=80,
            placeholder="Or paste a brief summary of your experience, skills, and projects…",
            label_visibility="collapsed",
        )
        st.session_state["resume_typed"] = typed_background

        uploaded_resume = st.file_uploader(
            "Upload resume (PDF, Word, or TXT)",
            type=["pdf", "docx", "txt"],
            help="Optional. We extract text from your resume to personalize interview questions.",
        )

        _sync_resume_from_sources(typed_background, uploaded_resume)

        resume_file_name = st.session_state.get("resume_file_name", "")
        if resume_file_name and not uploaded_resume:
            st.caption(f"Resume loaded: **{resume_file_name}** (upload a new file to replace)")

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        _mode_selector_fragment()

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
        _duration_selector_fragment()

        st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

        if st.button("Begin Mock Interview →", type="primary", use_container_width=True):
            job_details = st.session_state.get("job_description", "").strip()
            if not job_details:
                show_validation_error(
                    "Please enter **job details** before starting your mock interview."
                )
            else:
                st.session_state["_start_requested"] = True
                st.session_state["ai_voice_enabled"] = True


def render_landing_view() -> None:
    """Alias for setup view — kept for backward compatibility."""
    render_setup_view()
