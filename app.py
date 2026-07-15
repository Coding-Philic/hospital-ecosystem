"""
MediFlow AI — Main Application Entry Point
=============================================
Multi-Agent Hospital Orchestration Platform
Powered by Groq AI + LangGraph + Supabase

This is the main Streamlit app entry point.
Handles authentication, routing, and global theming.
"""

import streamlit as st
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from streamlit_cookies_controller import CookieController
from config import config
from database.supabase_client import is_authenticated, get_user_role, get_current_user, restore_session_from_cookies
from components.auth import render_auth_page, require_auth, render_logout_button

# ── Page Configuration ────────────────────────────────────────
st.set_page_config(
    page_title="MediFlow AI — Hospital Orchestration",
    page_icon="M",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "About": "MediFlow AI v1.0.0 — Multi-Agent Hospital Orchestration Platform",
    },
)

# ── Theme Management ─────────────────────────────────────────
if "theme" not in st.session_state:
    st.session_state.theme = "light"

if st.session_state.theme == "dark":
    theme_css = """
    :root {
        --bg-color: #0f172a;
        --card-bg: #1e293b;
        --border-color: #334155;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --accent: #007B8A;
        --accent-hover: #005F6B;
        --accent-light: #6BCBEB;
        --accent-lightest: #A2DFF7;
        --accent-blue: #3A9AD9;
    }
    """
else:
    theme_css = """
    :root {
        --bg-color: #ffffff;
        --card-bg: #f8fafc;
        --border-color: #e2e8f0;
        --text-primary: #1e293b;
        --text-secondary: #64748b;
        --accent: #007B8A;
        --accent-hover: #005F6B;
        --accent-light: #6BCBEB;
        --accent-lightest: #A2DFF7;
        --accent-blue: #3A9AD9;
    }
    """

st.markdown(f"""
<style>
    {theme_css}

    /* ── Import Google Font ─────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ── Global Styling ─────────────────────────────────── */
    html, body, [class*="css"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    .stApp {{
        background: var(--bg-color);
        color: var(--text-primary) !important;
    }}

    /* ── Hide Native Sidebar Completely ─────────────────── */
    section[data-testid="stSidebar"] {{
        display: none !important;
    }}
    button[kind="header"] {{
        display: none !important;
    }}

    /* ── Headers & Text ─────────────────────────────────── */
    h1, h2, h3, h4, h5, h6, p, span, div {{
        font-family: 'Inter', sans-serif !important;
        color: var(--text-primary) !important;
    }}

    h1 {{
        color: var(--accent) !important;
        font-weight: 800 !important;
        letter-spacing: -0.02em !important;
    }}

    h2, h3 {{
        font-weight: 700 !important;
    }}

    .stMarkdown p {{
        color: var(--text-primary) !important;
    }}

    /* ── Cards / Containers ─────────────────────────────── */
    .stExpander {{
        background: var(--card-bg) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 6px !important;
        box-shadow: none !important;
    }}

    div[data-testid="stForm"] {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 2rem;
    }}

    /* ── Buttons ─────────────────────────────────────────── */
    .stButton > button {{
        border-radius: 4px !important;
        font-weight: 600 !important;
        border: 1px solid var(--border-color) !important;
        background: var(--card-bg) !important;
        color: var(--text-primary) !important;
        transition: all 0.15s ease !important;
        box-shadow: none !important;
    }}

    .stButton > button:hover {{
        border-color: var(--accent) !important;
        color: var(--accent) !important;
    }}

    .stButton > button[kind="primary"] {{
        background: var(--accent) !important;
        color: #ffffff !important;
        border: none !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        background: var(--accent-hover) !important;
        color: #ffffff !important;
    }}

    /* ── Inputs ──────────────────────────────────────────── */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {{
        background: var(--bg-color) !important;
        border: 1px solid var(--border-color) !important;
        border-radius: 4px !important;
        color: var(--text-primary) !important;
    }}

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 1px var(--accent) !important;
    }}

    /* ── Metrics ─────────────────────────────────────────── */
    [data-testid="stMetric"] {{
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 6px;
        padding: 1.5rem;
        box-shadow: none !important;
    }}

    [data-testid="stMetricValue"] {{
        color: var(--accent) !important;
    }}

    [data-testid="stMetricLabel"] {{
        color: var(--text-secondary) !important;
    }}

    /* ── Tabs ────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0px;
        background: transparent;
        border-bottom: 1px solid var(--border-color);
        padding: 0px;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 0px;
        color: var(--text-secondary);
        padding: 12px 24px;
        border-bottom: 2px solid transparent;
        background: transparent;
    }}

    .stTabs [aria-selected="true"] {{
        color: var(--accent) !important;
        border-bottom: 2px solid var(--accent) !important;
        background: transparent !important;
    }}

    /* ── Alerts ──────────────────────────────────────────── */
    .stAlert {{
        border-radius: 4px !important;
        border: 1px solid var(--border-color) !important;
        background-color: var(--card-bg) !important;
        color: var(--text-primary) !important;
    }}

    /* ── DataFrames ──────────────────────────────────────── */
    .stDataFrame {{
        border-radius: 6px;
        border: 1px solid var(--border-color);
        background: var(--card-bg);
    }}

    /* ── Horizontal Dividers ─────────────────────────────── */
    hr {{
        border-color: var(--border-color) !important;
    }}

    /* ── Hide Streamlit Branding ─────────────────────────── */
    #MainMenu {{ visibility: hidden; }}
    footer {{ visibility: hidden; }}

    /* ── Responsive Mobile Styles ────────────────────────── */
    @media (max-width: 768px) {{
        div[data-testid="stForm"] {{
            padding: 1rem;
        }}
        .stTabs [data-baseweb="tab"] {{
            padding: 8px 12px;
            font-size: 0.85rem;
        }}
        [data-testid="column"] {{
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
            margin-bottom: 1rem;
        }}
    }}
</style>
""", unsafe_allow_html=True)


# ── Cookie Controller & Session Persistence ───────────────────
# Initialize cookie controller (must be called early, renders a hidden component)
cookie_controller = CookieController()

# Store controller in session_state so auth components can access it
st.session_state["_cookie_controller"] = cookie_controller

import time
if "_pending_redirect" in st.session_state:
    time.sleep(0.5) # Give client time to save cookie before page swap
    target = st.session_state.pop("_pending_redirect")
    st.switch_page(target)

# Attempt to restore session from cookies (survives page refresh)
if not is_authenticated():
    restored = restore_session_from_cookies(cookie_controller)
    if restored:
        st.rerun()  # Re-render page in authenticated state

# ── Main Application Logic ────────────────────────────────────

if not is_authenticated():
    # Show auth page
    render_auth_page()
else:
    role = get_user_role()
    role_page_map = {
        "patient": "pages/1_Patient_Portal.py",
        "receptionist": "pages/2_Reception_Dashboard.py",
        "doctor": "pages/3_Doctor_Dashboard.py",
        "pharmacist": "pages/4_Pharmacy_Dashboard.py",
        "admin": "pages/5_Admin_Dashboard.py"
    }
    target_page = role_page_map.get(role)
    if target_page and os.path.exists(os.path.join(os.path.dirname(__file__), target_page)):
        st.session_state["_pending_redirect"] = target_page
        st.rerun()
    else:
        st.error(f"Dashboard for role '{role}' not found.")
        render_logout_button()
