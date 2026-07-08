"""Modern UI styles injected into Streamlit."""

from __future__ import annotations

import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

#MainMenu, footer, header { visibility: hidden; }

.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 100%;
    padding-left: 2rem;
    padding-right: 2rem;
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
[class*="st-key-dur_"] button,
[class*="st-key-input_"] button {
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
[class*="st-key-dur_"] button:hover,
[class*="st-key-input_"] button:hover {
    border-color: #a5b4fc !important;
    background: #f5f3ff !important;
    box-shadow: 0 2px 8px rgba(99,102,241,0.1) !important;
}

.hero-section {
    text-align: center;
    padding: 2.5rem 1rem 2rem;
    margin-bottom: 1.5rem;
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
    margin: 0 auto;
    line-height: 1.6;
    text-align: center;
    display: block;
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
    padding: 1.5rem 2rem;
    color: white;
    margin-bottom: 1.5rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
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
</style>
"""


def inject_styles() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
