"""
MediFlow AI — Navbar Navigation Component
=============================================
Top horizontal navbar with user info, navigation links, and actions.
Responsive layout supporting Desktop, Tablet, and Mobile.
"""

import streamlit as st
import os
from database.supabase_client import get_current_user, get_user_role
from database import queries as db
from components.auth import render_logout_button
from utils.constants import COLORS

def get_navbar_css():
    return """
    <style>
        /* Hide default padding so navbar sits at top */
        .block-container { padding-top: 1.5rem !important; }
        
        /* ------------------------------------------- */
        /* GENERAL NAVBAR COMPONENT STYLING */
        /* ------------------------------------------- */
        .desktop-profile-box {
            display: flex;
            align-items: center;
            gap: 12px;
            background-color: #1f2937;
            padding: 6px 12px;
            border-radius: 10px;
            border: 1px solid #374151;
            width: fit-content;
            margin: 0 auto;
        }
        .desktop-profile-avatar {
            background-color: #374151;
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 14px;
        }
        .desktop-profile-text { line-height: 1.2; text-align: left; }
        .desktop-profile-name { color: white; font-size: 0.85rem; font-weight: 600; white-space: nowrap; }
        .desktop-profile-role { color: #9ca3af; font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.5px; }

        /* Shared base for all navbar containers */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) {
            background-color: #111827;
            border-radius: 12px;
            padding: 12px 24px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
            border: 1px solid #1f2937;
            margin-bottom: 25px;
        }

        /* Center contents inside navbar columns */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) div[data-testid="column"] {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Shared Tab Buttons Styling */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) button[kind="secondary"] {
            background-color: transparent !important;
            border: 1px solid #374151 !important;
            color: #9ca3af !important;
            border-radius: 20px !important;
            transition: all 0.3s ease !important;
            min-height: 0 !important;
            padding: 4px 16px !important;
            white-space: nowrap !important;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) button[kind="secondary"]:hover {
            border-color: #6b7280 !important;
            color: white !important;
        }

        /* Shared Tab Buttons - Active */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) button[kind="primary"] {
            background: linear-gradient(90deg, #ff7e5f, #feb47b) !important;
            border: none !important;
            color: white !important;
            border-radius: 20px !important;
            box-shadow: 0 0 15px rgba(255, 126, 95, 0.4) !important;
            font-weight: 600 !important;
            min-height: 0 !important;
            padding: 4px 16px !important;
            white-space: nowrap !important;
        }

        /* Mobile specific styling */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) > div > div > div > div {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) button[kind="secondary"] {
            background-color: #1f2937 !important;
            border: 1px solid #374151 !important;
            color: white !important;
            border-radius: 8px !important;
            padding: 4px 12px !important;
        }
        /* Hide caret icon in Mobile popover */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) button[kind="secondary"] svg {
            display: none !important;
        }


        /* ------------------------------------------- */
        /* MEDIA QUERIES FOR RESPONSIVE DISPLAY */
        /* ------------------------------------------- */
        
        /* Desktop: Show ONLY if > 1100px */
        @media (max-width: 1100px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .desktop-nav-hook) { display: none !important; }
        }

        /* Tablet: Show ONLY between 768px and 1100px */
        @media (min-width: 1101px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .tablet-nav-hook) { display: none !important; }
        }
        @media (max-width: 767px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .tablet-nav-hook) { display: none !important; }
        }

        /* Mobile: Show ONLY if < 768px */
        @media (min-width: 768px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) { display: none !important; }
        }
    </style>
    """

def render_navbar():
    """Render the responsive top navbar with navigation links and actions."""
    profile = get_current_user()
    if not profile:
        return

    role = profile.get("role", "patient")
    full_name = profile.get("full_name", "User")
    
    # Define tabs for each role
    ROLE_TABS = {
        "patient": ["New Visit", "My Queue", "Prescriptions", "Visit History", "My Profile"],
        "receptionist": ["Live Queue", "Triage Confirmation", "Register Patient", "Search", "Workflow Overview"],
        "doctor": ["Patient Queue", "Consultation", "Prescribe", "Patient History", "Settings"],
        "pharmacist": ["Prescription Queue", "Inventory", "Substitutions", "Dispense"],
        "admin": ["Analytics", "Doctors", "Users", "Departments", "Audit Trail"]
    }
    
    tabs = ROLE_TABS.get(role, [])
    if not tabs:
        return

    if "active_tab" not in st.session_state or st.session_state.active_tab not in tabs:
        st.session_state.active_tab = tabs[0]
        
    current_theme = st.session_state.get("theme", "light")
    theme_icon = "🌙" if current_theme == "light" else "☀️"

    # Profile HTML string (reused across Desktop/Tablet)
    profile_html = f"""
    <div class="desktop-profile-box">
        <div class="desktop-profile-avatar">👤</div>
        <div class="desktop-profile-text">
            <div class="desktop-profile-name">{full_name}</div>
            <div class="desktop-profile-role">{role}</div>
        </div>
    </div>
    """

    # Inject CSS
    st.markdown(get_navbar_css(), unsafe_allow_html=True)

    # ==========================================
    # DESKTOP NAVBAR (> 1100px)
    # ==========================================
    desktop_container = st.container()
    with desktop_container:
        st.markdown('<span class="nav-hook desktop-nav-hook"></span>', unsafe_allow_html=True)
        # Layout: Brand (15%), Tabs (60%), Profile/Actions (25%)
        brand_col, tabs_col, actions_col = st.columns([1.5, 6, 2.5])
        
        with brand_col:
            st.markdown('<h4 style="color: white; margin:0; padding-top:6px; white-space:nowrap;">MediFlow <span style="color:#3A9AD9">AI</span></h4>', unsafe_allow_html=True)
            
        with tabs_col:
            # Render horizontal tabs
            tab_cols = st.columns(len(tabs))
            for i, tab in enumerate(tabs):
                with tab_cols[i]:
                    btn_type = "primary" if st.session_state.active_tab == tab else "secondary"
                    if st.button(tab, key=f"d_tab_{tab}", use_container_width=True, type=btn_type):
                        st.session_state.active_tab = tab
                        st.rerun()
                        
        with actions_col:
            p_col1, p_col2, p_col3, p_col4 = st.columns([5, 1.5, 1.5, 3])
            with p_col1:
                st.markdown(profile_html, unsafe_allow_html=True)
            with p_col2:
                if st.button(theme_icon, key="d_theme", help="Toggle Theme"):
                    st.session_state.theme = "dark" if current_theme == "light" else "light"
                    st.rerun()
            with p_col3:
                if st.button("🔄", key="d_ref", help="Refresh"):
                    st.rerun()
            with p_col4:
                render_logout_button(key="d_logout")


    # ==========================================
    # TABLET NAVBAR (768px - 1100px)
    # ==========================================
    tablet_container = st.container()
    with tablet_container:
        st.markdown('<span class="nav-hook tablet-nav-hook"></span>', unsafe_allow_html=True)
        # Top Row: Brand & Actions
        t_brand_col, t_actions_col = st.columns([3, 7])
        
        with t_brand_col:
            st.markdown('<h4 style="color: white; margin:0; padding-top:6px;">MediFlow <span style="color:#3A9AD9">AI</span></h4>', unsafe_allow_html=True)
            
        with t_actions_col:
            tp_col0, tp_col1, tp_col2, tp_col3, tp_col4 = st.columns([2, 5, 1.5, 1.5, 3])
            # tp_col0 is empty spacer to push actions to the right
            with tp_col1:
                st.markdown(profile_html, unsafe_allow_html=True)
            with tp_col2:
                if st.button(theme_icon, key="t_theme", help="Toggle Theme"):
                    st.session_state.theme = "dark" if current_theme == "light" else "light"
                    st.rerun()
            with tp_col3:
                if st.button("🔄", key="t_ref", help="Refresh"):
                    st.rerun()
            with tp_col4:
                render_logout_button(key="t_logout")
                
        # Bottom Row: Horizontal Tabs
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        t_tab_cols = st.columns(len(tabs))
        for i, tab in enumerate(tabs):
            with t_tab_cols[i]:
                btn_type = "primary" if st.session_state.active_tab == tab else "secondary"
                if st.button(tab, key=f"t_tab_{tab}", use_container_width=True, type=btn_type):
                    st.session_state.active_tab = tab
                    st.rerun()


    # ==========================================
    # MOBILE NAVBAR (< 768px)
    # ==========================================
    mobile_container = st.container()
    with mobile_container:
        st.markdown('<span class="nav-hook mobile-nav-hook"></span>', unsafe_allow_html=True)
        m_brand_col, m_btn_col = st.columns([4, 1])
        
        with m_brand_col:
            st.markdown('<h4 style="color: white; margin:0;">MediFlow <span style="color:#3A9AD9">AI</span></h4>', unsafe_allow_html=True)
            
        with m_btn_col:
            with st.popover("☰", use_container_width=True):
                # Profile Info in popover
                st.markdown(f"""
                <div style="background-color: #1f2937; padding: 12px; border-radius: 8px; margin-bottom: 12px; display: flex; align-items: center; gap: 10px;">
                    <div style="background-color: #374151; color: white; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center;">👤</div>
                    <div style="line-height: 1.2;">
                        <div style="color: white; font-size: 0.9rem; font-weight: 700;">{full_name}</div>
                        <div style="color: #9ca3af; font-size: 0.7rem; text-transform: uppercase; font-weight: 600;">{role}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Render vertical tabs
                st.markdown("**Navigation**")
                for tab in tabs:
                    btn_type = "primary" if st.session_state.active_tab == tab else "secondary"
                    if st.button(tab, key=f"m_tab_{tab}", use_container_width=True, type=btn_type):
                        st.session_state.active_tab = tab
                        st.rerun()
                        
                st.markdown("---")
                
                # Actions
                if st.button(f"{theme_icon} Toggle Theme", key="m_theme", use_container_width=True):
                    st.session_state.theme = "dark" if current_theme == "light" else "light"
                    st.rerun()
                    
                if st.button("🔄 Refresh Data", key="m_ref", use_container_width=True):
                    st.rerun()
                    
                render_logout_button(key="m_logout")
                
    # Optional quick actions row if needed (for specific roles like Doctor status)
    _render_quick_actions(role, profile)


def _render_quick_actions(role: str, profile: dict):
    """Render role-specific quick action widgets horizontally below navbar."""
    if role == "doctor":
        try:
            doctor = db.get_doctor_by_user_id(profile["id"])
            if doctor:
                current_status = doctor.get("status", "offline")
                status_options = ["available", "busy", "on_break", "offline"]
                
                new_status = st.selectbox(
                    "My Status",
                    options=status_options,
                    index=status_options.index(current_status),
                    format_func=lambda x: x.replace("_", " ").title(),
                    key="doctor_status_navbar",
                )
                if new_status != current_status:
                    db.update_doctor_status(doctor["id"], new_status)
                    st.success(f"Status updated to {new_status.title()}")
                    st.rerun()
        except Exception:
            pass

    elif role == "receptionist":
        try:
            stats = db.get_today_stats()
            st.markdown(f"**Today's Overview:** Waiting: {stats.get('waiting_patients', 0)} | Completed: {stats.get('completed_consultations', 0)}")
        except Exception:
            pass

    elif role == "pharmacist":
        try:
            low_stock = db.get_low_stock_items()
            if low_stock:
                st.warning(f"{len(low_stock)} items below reorder level")
        except Exception:
            pass
