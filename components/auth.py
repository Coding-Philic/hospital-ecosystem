"""
MediFlow AI — Authentication Components
=========================================
Login, Sign-up, and session management UI components for Streamlit.
With cookie-based session persistence for surviving page refreshes.
"""

import streamlit as st
from database.supabase_client import (
    sign_up, sign_in, sign_out, is_authenticated, get_user_role,
    save_session_to_cookies,
)
from database import queries as db
from config import config
from utils.helpers import generate_patient_id


def render_auth_page():
    """Render the professional landing and authentication page."""
    view = st.session_state.get("auth_view", "landing")

    if view == "landing":
        _render_landing_page()
    elif view == "login":
        _render_login_form()
    elif view == "signup":
        _render_signup_form()

def _render_landing_page():
    # Top Navbar (Landing Page)
    st.markdown("""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 1rem 0; border-bottom: 1px solid var(--border-color); margin-bottom: 2rem;">
            <div style="font-weight: 800; font-size: 1.5rem; color: var(--accent);">MediFlow AI</div>
            <div style="color: var(--text-secondary); font-size: 0.9rem;">Hospital Orchestration Platform</div>
        </div>
    """, unsafe_allow_html=True)

    # Hero Section
    st.markdown("""
    <div style="padding: 3rem 0 2rem 0; text-align: center;">
        <div style="color: var(--accent); font-size: 3.5rem; font-weight: 800; margin-bottom: 0.5rem; line-height: 1.2;">Streamlining Healthcare,<br>Empowering Lives</div>
        <div style="color: var(--text-secondary); font-size: 1.2rem; margin-bottom: 2rem;">The complete AI-powered operating system for modern hospitals.</div>
    </div>
    """, unsafe_allow_html=True)
    
    st.image("https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?q=80&w=2053&auto=format&fit=crop", use_container_width=True)

    # Trust Metrics
    st.markdown("<br><br>", unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.markdown("<div style='text-align: center;'><div style='color: var(--accent); font-size: 2rem; font-weight: 700;'>50+</div><div style='color: var(--text-secondary); font-size: 0.9rem; font-weight: 500; text-transform: uppercase;'>Specialist Doctors</div></div>", unsafe_allow_html=True)
    with m2:
        st.markdown("<div style='text-align: center;'><div style='color: var(--accent); font-size: 2rem; font-weight: 700;'>10k+</div><div style='color: var(--text-secondary); font-size: 0.9rem; font-weight: 500; text-transform: uppercase;'>Patients Treated</div></div>", unsafe_allow_html=True)
    with m3:
        st.markdown("<div style='text-align: center;'><div style='color: var(--accent); font-size: 2rem; font-weight: 700;'>24/7</div><div style='color: var(--text-secondary); font-size: 0.9rem; font-weight: 500; text-transform: uppercase;'>AI Triage</div></div>", unsafe_allow_html=True)
    with m4:
        st.markdown("<div style='text-align: center;'><div style='color: var(--accent); font-size: 2rem; font-weight: 700;'>99.9%</div><div style='color: var(--text-secondary); font-size: 0.9rem; font-weight: 500; text-transform: uppercase;'>Uptime</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br><br><hr>", unsafe_allow_html=True)
    
    # Bottom Buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col2:
        if st.button("Log In", use_container_width=True, type="primary"):
            st.session_state.auth_view = "login"
            st.rerun()
    with col3:
        if st.button("Sign Up", use_container_width=True):
            st.session_state.auth_view = "signup"
            st.rerun()


def _render_login_form():
    """Render the login form."""
    st.markdown("<div style='max-width: 500px; margin: 0 auto; padding: 2rem; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px;'>", unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        st.markdown("##### Welcome Back")

        email = st.text_input("Email", placeholder="you@example.com", key="login_email")
        password = st.text_input("Password", type="password", placeholder="••••••••", key="login_password")

        submitted = st.form_submit_button("Login", use_container_width=True, type="primary")

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Signing in..."):
                    result = sign_in(email, password)

                if result["success"]:
                    st.session_state["authenticated"] = True
                    st.session_state["user"] = result["user"]
                    st.session_state["session"] = result["session"]
                    st.session_state["profile"] = result["profile"]
                    st.session_state["role"] = result["profile"].get("role", "patient")

                    cookie_ctrl = st.session_state.get("_cookie_controller")
                    if cookie_ctrl and result.get("session"):
                        save_session_to_cookies(cookie_ctrl, result["session"])

                    st.success(result["message"])
                    
                    # Redirect to appropriate dashboard
                    role_page_map = {
                        "patient": "pages/1_Patient_Portal.py",
                        "receptionist": "pages/2_Reception_Dashboard.py",
                        "doctor": "pages/3_Doctor_Dashboard.py",
                        "pharmacist": "pages/4_Pharmacy_Dashboard.py",
                        "admin": "pages/5_Admin_Dashboard.py"
                    }
                    target_page = role_page_map.get(st.session_state["role"])
                    if target_page:
                        st.switch_page(target_page)
                    else:
                        st.rerun()
                else:
                    st.error(result["message"])
                    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Don't have an account? Sign Up", use_container_width=True):
            st.session_state.auth_view = "signup"
            st.rerun()


def _render_signup_form():
    """Render the signup form."""
    st.markdown("<div style='max-width: 500px; margin: 0 auto; padding: 2rem; background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px;'>", unsafe_allow_html=True)
    with st.form("signup_form", clear_on_submit=False):
        st.markdown("##### Create Your Account")

        full_name = st.text_input("Full Name", placeholder="John Doe", key="signup_name")
        email = st.text_input("Email", placeholder="you@example.com", key="signup_email")
        phone = st.text_input("Phone Number", placeholder="+91 98765 43210", key="signup_phone")
        password = st.text_input("Password", type="password", placeholder="Min. 6 characters", key="signup_password")
        confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")

        role = st.selectbox(
            "I am a...",
            options=config.USER_ROLES,
            format_func=lambda x: x.title(),
            key="signup_role",
        )

        submitted = st.form_submit_button("Register", use_container_width=True, type="primary")

        if submitted:
            if not all([full_name, email, password, confirm_password]):
                st.error("Please fill in all required fields.")
            elif password != confirm_password:
                st.error("Passwords do not match.")
            elif len(password) < 6:
                st.error("Password must be at least 6 characters.")
            else:
                with st.spinner("Creating your account..."):
                    result = sign_up(email, password, full_name, role, phone)

                if result["success"]:
                    if role == "patient" and result.get("user"):
                        try:
                            patient_code = generate_patient_id()
                            db.create_patient({
                                "user_id": str(result["user"].id),
                                "patient_id_code": patient_code,
                            })
                        except Exception:
                            pass

                    st.success("✅ Account created! Please sign in.")
                    st.session_state.auth_view = "login"
                    st.rerun()
                else:
                    st.error(result["message"])
                    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Already have an account? Log In", use_container_width=True):
            st.session_state.auth_view = "login"
            st.rerun()


def render_logout_button(key: str = None):
    """Render a logout button."""
    if st.button("Sign Out", key=key, use_container_width=True):
        cookie_ctrl = st.session_state.get("_cookie_controller")
        sign_out(cookie_controller=cookie_ctrl)
        st.rerun()


def require_auth(allowed_roles: list = None):
    """
    Authentication guard. Call at the top of each page.
    If not authenticated, attempts to restore session from cookies first.
    If still not authenticated, shows the auth page.
    If authenticated but wrong role, shows access denied.

    Args:
        allowed_roles: List of roles allowed to access this page.
                      None = any authenticated user.

    Returns:
        True if authenticated and authorized, else halts page.
    """
    # Attempt cookie-based session restoration before auth check
    if not is_authenticated():
        try:
            from streamlit_cookies_controller import CookieController
            from database.supabase_client import restore_session_from_cookies

            # Reuse existing controller or create one for this page
            if "_cookie_controller" not in st.session_state:
                cookie_ctrl = CookieController()
                st.session_state["_cookie_controller"] = cookie_ctrl
            else:
                cookie_ctrl = st.session_state["_cookie_controller"]

            restored = restore_session_from_cookies(cookie_ctrl)
            if restored:
                st.rerun()  # Re-render page in authenticated state
        except Exception:
            pass  # Fall through to normal auth check

    if not is_authenticated():
        render_auth_page()
        st.stop()
        return False

    if allowed_roles:
        user_role = get_user_role()
        if user_role not in allowed_roles:
            st.error(f"Access Denied. This page requires one of: {', '.join(allowed_roles)}")
            st.info(f"You are logged in as: **{user_role}**")
            render_logout_button()
            st.stop()
            return False

    return True
