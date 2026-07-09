"""Modern UI styles injected into Streamlit."""

from __future__ import annotations

import streamlit as st

CUSTOM_CSS = """
<style>

html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

#MainMenu, footer, header { visibility: hidden; }

/* Center all page content — works with @st.fragment (columns do not). */
section.main > div.block-container {
    max-width: 52rem !important;
    margin-left: auto !important;
    margin-right: auto !important;
    padding-top: 0.35rem;
    padding-bottom: 2rem;
    padding-left: max(2.5rem, 10vw);
    padding-right: max(2.5rem, 10vw);
}

.setup-section {
    text-align: center;
}

.section-spacer {
    height: 1.75rem;
}

/* Center Streamlit widgets inside the setup form */
.block-container h4 {
    text-align: center;
    margin-bottom: 0.25rem;
}

.block-container .stCaption, .block-container [data-testid="stCaptionContainer"] {
    text-align: center;
}

.block-container [data-testid="stRadio"] {
    display: flex;
    justify-content: center;
}

.block-container [data-testid="stRadio"] > div {
    justify-content: center;
    gap: 1.5rem;
}

/* Shared clickable option cards */
[class*="st-key-mode_"] button,
[class*="st-key-dur_"] button {
    min-height: 132px;
    height: auto !important;
    padding: 1.1rem 0.85rem !important;
    border-radius: 12px !important;
    border: 2px solid #e2e8f0 !important;
    background: #f8fafc !important;
    color: #1e293b !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    line-height: 1.4 !important;
    white-space: pre-line !important;
    box-shadow: none !important;
    transition: border-color 0.12s ease, background 0.12s ease !important;
}

[class*="st-key-dur_"] button {
    min-height: 148px;
    font-size: 0.82rem !important;
}

[class*="st-key-mode_"] button:hover,
[class*="st-key-dur_"] button:hover {
    border-color: #a5b4fc !important;
    background: #f5f3ff !important;
    box-shadow: 0 2px 8px rgba(99,102,241,0.1) !important;
}

[class*="st-key-mode_"] button[kind="primary"],
[class*="st-key-dur_"] button[kind="primary"] {
    background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%) !important;
    border: 2px solid #6366f1 !important;
    color: #1e293b !important;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15) !important;
}

.hero-section {
    text-align: center;
    padding: 1rem 1rem 1.25rem;
    margin-bottom: 1rem;
    display: flex;
    flex-direction: column;
    align-items: center;
}

.hero-subtitle-wrap {
    width: 100%;
    display: flex;
    justify-content: center;
    margin-bottom: 0.25rem;
}

.hero-badge {
    display: inline-block;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0.35rem 1rem;
    border-radius: 999px;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    margin-bottom: 1rem;
}

.hero-title {
    font-size: 2.75rem;
    font-weight: 800;
    background: linear-gradient(135deg, #1e1b4b 0%, #4338ca 50%, #7c3aed 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 0.75rem 0;
    line-height: 1.15;
}

.hero-subtitle {
    font-size: 1.1rem;
    color: #64748b;
    max-width: 720px;
    width: 100%;
    margin: 0;
    line-height: 1.6;
    text-align: center;
}

.setup-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1.75rem;
    margin-bottom: 1.25rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04), 0 4px 12px rgba(99,102,241,0.06);
}

.setup-card-title {
    font-size: 1rem;
    font-weight: 700;
    color: #1e293b;
    margin: 0 0 0.25rem 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.setup-card-desc {
    font-size: 0.85rem;
    color: #94a3b8;
    margin: 0 0 1rem 0;
}

.mode-card {
    background: #f8fafc;
    border: 2px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem;
    text-align: center;
    cursor: pointer;
    transition: all 0.2s ease;
    height: 100%;
}

.mode-card:hover {
    border-color: #a5b4fc;
    background: #f5f3ff;
}

.mode-card-active {
    background: linear-gradient(135deg, #eef2ff 0%, #f5f3ff 100%);
    border: 2px solid #6366f1;
    box-shadow: 0 0 0 3px rgba(99,102,241,0.15);
}

.mode-icon { font-size: 2rem; margin-bottom: 0.5rem; }
.mode-label { font-weight: 700; color: #1e293b; font-size: 0.95rem; }
.mode-desc { font-size: 0.8rem; color: #64748b; margin-top: 0.25rem; }

.duration-pill {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.65rem 1.5rem;
    border-radius: 999px;
    font-weight: 600;
    font-size: 0.9rem;
    border: 2px solid #e2e8f0;
    background: #f8fafc;
    color: #475569;
    margin: 0.25rem;
}

.duration-pill-active {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: white;
    border-color: transparent;
    box-shadow: 0 4px 14px rgba(99,102,241,0.35);
}

.interview-header {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
    border-radius: 16px;
    padding: 1.25rem 1.5rem;
    color: white;
    margin-bottom: 1.5rem;
    width: 100%;
    box-sizing: border-box;
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.interview-header-marker {
    display: none;
}

/* Full-width purple header row: title + timer + End Interview */
div:has(> div > .interview-header-marker) + div[data-testid="stHorizontalBlock"],
div:has(> .interview-header-marker) + div[data-testid="stHorizontalBlock"] {
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);
    border-radius: 16px;
    padding: 1.15rem 1.35rem;
    margin-bottom: 1.5rem;
    align-items: center;
    gap: 0.75rem;
    width: 100%;
    box-sizing: border-box;
}

div:has(> div > .interview-header-marker) + div[data-testid="stHorizontalBlock"] .interview-header-title,
div:has(> .interview-header-marker) + div[data-testid="stHorizontalBlock"] .interview-header-title,
div:has(> div > .interview-header-marker) + div[data-testid="stHorizontalBlock"] .status-badge,
div:has(> .interview-header-marker) + div[data-testid="stHorizontalBlock"] .status-badge,
div:has(> div > .interview-header-marker) + div[data-testid="stHorizontalBlock"] .interview-timer,
div:has(> .interview-header-marker) + div[data-testid="stHorizontalBlock"] .interview-timer {
    color: white;
}

div:has(> div > .interview-header-marker) + div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button,
div:has(> .interview-header-marker) + div[data-testid="stHorizontalBlock"] div[data-testid="stButton"] > button {
    background: rgba(255, 255, 255, 0.95) !important;
    color: #312e81 !important;
    border: none !important;
    font-weight: 600;
}

.interview-header-title { font-size: 1.1rem; font-weight: 600; opacity: 0.9; }
.interview-timer {
    font-size: 2rem;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.02em;
}

.interview-timer-warning { color: #fbbf24; }
.interview-timer-critical { color: #f87171; animation: pulse 1s infinite; }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}

.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    background: rgba(255,255,255,0.15);
    padding: 0.35rem 0.85rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 500;
}

.status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #4ade80;
    animation: blink 1.5s infinite;
}

@keyframes blink {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

.chat-container {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1rem;
    min-height: 320px;
    max-height: 480px;
    overflow-y: auto;
    margin-bottom: 1rem;
}

/* Zoom-like meeting room */
.meeting-room {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    min-height: 340px;
    display: flex;
    flex-direction: column;
}

.meeting-participants {
    display: flex;
    gap: 1rem;
    justify-content: center;
    flex: 1;
    align-items: center;
    flex-wrap: wrap;
}

.participant-tile {
    background: #334155;
    border-radius: 12px;
    padding: 1.5rem 1rem;
    width: 200px;
    min-height: 180px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border: 3px solid transparent;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.participant-tile.speaking {
    border-color: #22c55e;
    box-shadow: 0 0 0 2px rgba(34, 197, 94, 0.35), 0 0 24px rgba(34, 197, 94, 0.2);
}

.participant-avatar {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    background: #475569;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    margin-bottom: 0.75rem;
}

.participant-tile.speaking .participant-avatar {
    background: #166534;
}

.participant-name {
    color: #f1f5f9;
    font-weight: 600;
    font-size: 0.95rem;
    margin-bottom: 0.25rem;
}

.participant-status {
    color: #94a3b8;
    font-size: 0.75rem;
}

.participant-tile.speaking .participant-status {
    color: #4ade80;
}

.live-caption-bar {
    background: rgba(0, 0, 0, 0.75);
    border-radius: 8px;
    padding: 0.85rem 1.25rem;
    margin-top: 1rem;
    text-align: center;
    animation: caption-fade-in 0.25s ease;
}

.live-caption-speaker {
    color: #94a3b8;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.35rem;
}

.live-caption-text {
    color: #ffffff;
    font-size: 1rem;
    line-height: 1.5;
}

@keyframes caption-fade-in {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}

.meeting-controls {
    display: flex;
    gap: 0.75rem;
    justify-content: center;
    margin-top: 0.5rem;
}

.meeting-idle-hint {
    color: #64748b;
    font-size: 0.85rem;
    text-align: center;
    padding: 2rem 1rem;
}

.mic-active-hint {
    color: #4338ca;
    font-size: 0.95rem;
    font-weight: 600;
    text-align: center;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0 1rem;
    background: #eef2ff;
    border-radius: 12px;
    border: 1px solid #c7d2fe;
}

.cooldown-banner {
    text-align: center;
    padding: 1.25rem 1rem;
    margin: 1rem 0;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    color: #475569;
    font-size: 0.95rem;
}

.cooldown-banner strong {
    color: #4338ca;
    font-size: 1.25rem;
}

.eval-hero {
    text-align: center;
    padding: 2rem 1rem;
    background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
    border-radius: 16px;
    border: 1px solid #bbf7d0;
    margin-bottom: 1.5rem;
}

.eval-score-big {
    font-size: 4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #059669, #10b981);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1;
}

.eval-score-label { color: #64748b; font-size: 0.9rem; margin-top: 0.25rem; }

.metric-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem;
    text-align: center;
}

.metric-value { font-size: 1.75rem; font-weight: 700; color: #4338ca; }
.metric-label { font-size: 0.8rem; color: #64748b; margin-top: 0.25rem; }

.feedback-card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.25rem;
    height: 100%;
}

.feedback-card h4 { margin: 0 0 0.75rem 0; font-size: 0.95rem; color: #1e293b; }
.feedback-card ul { margin: 0; padding-left: 1.25rem; }
.feedback-card li { color: #475569; font-size: 0.9rem; margin-bottom: 0.35rem; }

.strengths-card { border-left: 4px solid #10b981; }
.improvements-card { border-left: 4px solid #f59e0b; }

div[data-testid="stSidebar"] { display: none; }
section[data-testid="stSidebar"] { display: none; }

.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border: none;
    border-radius: 12px;
    font-weight: 600;
    padding: 0.75rem 2rem;
    font-size: 1rem;
    box-shadow: 0 4px 14px rgba(99,102,241,0.35);
    transition: all 0.2s ease;
}

.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(99,102,241,0.45);
    transform: translateY(-1px);
}

.feature-row {
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-top: 2rem;
    flex-wrap: wrap;
}

.feature-item {
    text-align: center;
    max-width: 160px;
}

.feature-icon { font-size: 1.5rem; margin-bottom: 0.35rem; }
.feature-text { font-size: 0.8rem; color: #64748b; font-weight: 500; }

.generating-overlay {
    position: fixed;
    inset: 0;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 2rem;
    margin: 0;
    max-width: none;
    text-align: center;
    background: rgba(250, 251, 252, 0.94);
    backdrop-filter: blur(6px);
}

.generating-overlay-card {
    max-width: 420px;
    width: 100%;
}

.generating-spinner {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1.5rem;
}

.generating-square {
    width: 14px;
    height: 14px;
    border-radius: 4px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    animation: generating-bounce 1.2s ease-in-out infinite;
}

.generating-square:nth-child(2) { animation-delay: 0.15s; }
.generating-square:nth-child(3) { animation-delay: 0.3s; }
.generating-square:nth-child(4) { animation-delay: 0.45s; }

@keyframes generating-bounce {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.5; }
    40% { transform: scale(1); opacity: 1; }
}

.generating-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #1e293b;
    margin-bottom: 0.5rem;
}

.generating-subtitle {
    font-size: 0.9rem;
    color: #64748b;
    line-height: 1.5;
}
</style>
"""


def render_generating_overlay() -> None:
    st.markdown(
        """
        <div class="generating-overlay">
            <div class="generating-overlay-card">
                <div class="generating-spinner">
                    <div class="generating-square"></div>
                    <div class="generating-square"></div>
                    <div class="generating-square"></div>
                    <div class="generating-square"></div>
                </div>
                <div class="generating-title">Preparing your mock interview</div>
                <div class="generating-subtitle">
                    Tailoring questions to your role and generating the first question…
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def inject_styles() -> None:
    """Inject layout/CSS every run — Streamlit rebuilds the page on each rerun."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
