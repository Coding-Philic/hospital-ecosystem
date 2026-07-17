"""
MediFlow AI — Navbar Navigation Component (Redesigned UI)
=========================================================
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
        /* Modern CSS variables for easier color styling */
        :root {
            --brand-primary: #007B8A;
            --brand-secondary: #3A9AD9;
            --neutral-dark: #0f172a;
            --neutral-muted: #475569;
            --border-light: #e2e8f0;
            --bg-glass: rgba(255, 255, 255, 0.85);
            --shadow-sm: 0 1px 3px rgba(0,0,0,0.05), 0 1px 2px rgba(0,0,0,0.1);
            --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
            --radius-md: 8px;
        }

        /* Hide default padding so navbar sits neatly at the top */
        .block-container { padding-top: 1.5rem !important; }

        /* General container override for Streamlit block wrapper */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) {
            background-color: var(--bg-glass);
            backdrop-filter: blur(8px);
            -webkit-backdrop-filter: blur(8px);
            border-radius: var(--radius-md);
            padding: 12px 24px;
            border: 1px solid var(--border-light);
            box-shadow: var(--shadow-sm);
            margin-bottom: 24px;
            transition: all 0.2s ease;
        }

        /* ------------------------------------------- */
        /* MODERN PROFILE BOX STYLING */
        /* ------------------------------------------- */
        .desktop-profile-box {
            display: flex;
            align-items: center;
            gap: 12px;
            background-color: #f8fafc;
            padding: 6px 14px;
            border-radius: 6px;
            border: 1px solid var(--border-light);
            transition: all 0.2s ease;
        }
        .desktop-profile-box:hover {
            border-color: var(--brand-primary);
            background-color: #f1f5f9;
        }
        .desktop-profile-avatar {
            background: linear-gradient(135deg, var(--brand-primary), var(--brand-secondary));
            border-radius: 50%;
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 11px;
            font-weight: 700;
            box-shadow: 0 2px 4px rgba(0, 123, 138, 0.2);
        }
        .desktop-profile-text { line-height: 1.3; text-align: left; }
        .desktop-profile-name { color: var(--neutral-dark); font-size: 0.85rem; font-weight: 600; white-space: nowrap; }
        .desktop-profile-role { color: var(--brand-primary); font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.7px; font-weight: 700; }

        /* Ensure center vertical alignment inside layout rows */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) div[data-testid="column"] {
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* ------------------------------------------- */
        /* TAB BUTTONS STYLING */
        /* ------------------------------------------- */
        /* ------------------------------------------- */
        /* TWO-ROW LAYOUT FIXES (SCROLLABLE TABS)      */
        /* ------------------------------------------- */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .desktop-nav-hook) > div[data-testid="stHorizontalBlock"]:nth-of-type(2),
        div[data-testid="stVerticalBlock"]:has(> div.element-container .tablet-nav-hook) > div[data-testid="stHorizontalBlock"]:nth-of-type(2) {
            flex-wrap: nowrap !important;
            justify-content: flex-start !important;
            overflow-x: auto !important;
            scrollbar-width: none;
            padding-bottom: 2px !important;
            gap: 6px !important;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container .desktop-nav-hook) > div[data-testid="stHorizontalBlock"]:nth-of-type(2)::-webkit-scrollbar,
        div[data-testid="stVerticalBlock"]:has(> div.element-container .tablet-nav-hook) > div[data-testid="stHorizontalBlock"]:nth-of-type(2)::-webkit-scrollbar {
            display: none;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container .desktop-nav-hook) > div[data-testid="stHorizontalBlock"]:nth-of-type(2) > div[data-testid="column"],
        div[data-testid="stVerticalBlock"]:has(> div.element-container .tablet-nav-hook) > div[data-testid="stHorizontalBlock"]:nth-of-type(2) > div[data-testid="column"] {
            width: auto !important;
            flex: 0 0 auto !important;
            min-width: min-content !important;
        }

        /* Inactive Secondary Tab Button */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) button[kind="secondary"] {
            background-color: transparent !important;
            border: 1px solid transparent !important;
            color: var(--neutral-muted) !important;
            border-radius: 6px !important;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
            min-height: 0 !important;
            padding: 6px 12px !important;
            white-space: nowrap !important;
            font-size: 0.82rem !important;
            font-weight: 500 !important;
            margin: 0 !important;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) button[kind="secondary"]:hover {
            background-color: #f1f5f9 !important;
            color: var(--neutral-dark) !important;
        }

        /* Active Primary Tab Button */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) button[kind="primary"] {
            background: linear-gradient(135deg, var(--brand-primary), #006673) !important;
            border: none !important;
            color: white !important;
            border-radius: 6px !important;
            box-shadow: 0 2px 4px rgba(0, 123, 138, 0.2) !important;
            font-weight: 600 !important;
            min-height: 0 !important;
            padding: 6px 12px !important;
            white-space: nowrap !important;
            font-size: 0.82rem !important;
            margin: 0 !important;
            transition: transform 0.1s ease, box-shadow 0.15s ease !important;
        }
        div[data-testid="stVerticalBlock"]:has(> div.element-container .nav-hook) button[kind="primary"]:active {
            transform: scale(0.97);
        }

        /* ------------------------------------------- */
        /* MOBILE NAV DRAWER STYLING */
        /* ------------------------------------------- */
        div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) > div > div > div > div {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        /* Modern Slide-in Right Drawer (Mobile Popover) */
        div[data-testid="stPopoverBody"] {
            position: fixed !important;
            top: 0 !important;
            right: 0 !important;
            left: auto !important;
            height: 100vh !important;
            width: 320px !important;
            max-width: 85vw !important;
            margin: 0 !important;
            border-radius: 0 !important;
            border-left: 1px solid var(--border-light) !important;
            z-index: 999999 !important;
            box-shadow: -10px 0 25px rgba(15, 23, 42, 0.08) !important;
            overflow-y: auto !important;
            animation: drawerSlideIn 0.3s cubic-bezier(0.16, 1, 0.3, 1) forwards;
        }

        @keyframes drawerSlideIn {
            from { transform: translateX(100%); opacity: 0.9; }
            to { transform: translateX(0); opacity: 1; }
        }
        
        @keyframes drawerSlideOut {
            from { transform: translateX(0); opacity: 1; }
            to { transform: translateX(100%); opacity: 0.9; }
        }

        /* ------------------------------------------- */
        /* RESPONSIVE LAYOUT BREAKPOINTS */
        /* ------------------------------------------- */

        /* Desktop View (> 1100px) */
        @media (max-width: 1100px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .desktop-nav-hook) { display: none !important; }
        }

        /* Tablet View (768px - 1100px) */
        @media (min-width: 1101px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .tablet-nav-hook) { display: none !important; }
        }
        @media (max-width: 767px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .tablet-nav-hook) { display: none !important; }
        }

        /* Mobile View (< 768px) */
        @media (max-width: 767px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) {
                position: relative;
                min-height: 50px;
                padding: 10px 16px !important;
            }
            /* Position absolute for hamburger dropdown trigger */
            div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) div[data-testid="stPopover"] {
                position: absolute !important;
                top: 0 !important;
                bottom: 0 !important;
                margin: auto !important;
                right: 16px !important;
                height: 38px !important;
                width: auto !important;
                z-index: 100;
            }
            /* Style the pristine mobile trigger button */
            div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) div[data-testid="stPopover"] > button {
                background-color: #f8fafc !important;
                border: 1px solid var(--border-light) !important;
                padding: 0 !important;
                width: 42px !important;
                height: 38px !important;
                border-radius: 6px !important;
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                box-shadow: var(--shadow-sm) !important;
                transition: all 0.2s ease !important;
            }
            div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) div[data-testid="stPopover"] > button:hover {
                border-color: var(--brand-primary) !important;
                background-color: #f1f5f9 !important;
            }
            /* Hide Streamlit generic contents inside the popover button */
            div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) div[data-testid="stPopover"] > button > * {
                display: none !important;
            }
            /* Beautiful custom CSS Hamburger SVG Line Graphic */
            div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) div[data-testid="stPopover"] > button::after {
                content: "";
                width: 18px;
                height: 12px;
                background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke-width='2.5' stroke='%23475569'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' d='M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5'/%3E%3C/svg%3E");
                background-repeat: no-repeat;
                background-size: contain;
                display: block;
            }
        }

        /* Disable drawer CSS animation effects when not on mobile */
        @media (min-width: 768px) {
            div[data-testid="stVerticalBlock"]:has(> div.element-container .mobile-nav-hook) { display: none !important; }
            div[data-testid="stPopoverBody"] {
                animation: none !important;
                position: absolute !important;
                height: auto !important;
                width: auto !important;
            }
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
    initials = "".join([n[0].upper() for n in full_name.split()[:2]]) if full_name else "U"

    # Define tabs for each role (Unchanged)
    ROLE_TABS = {
        "patient": ["New Visit", "My Queue", "Prescriptions", "Visit History", "My Profile"],
        "receptionist": ["Live Queue", "Triage Confirmation", "Register Patient", "Search", "Workflow Overview", "Billing & Discharge"],
        "doctor": ["Patient Queue", "Consultation", "Prescribe", "Patient History", "Settings"],
        "pharmacist": ["Prescription Queue", "Inventory", "Substitutions", "Dispense"],
        "admin": ["Analytics", "Doctors", "Users", "Departments", "Audit Trail"]
    }

    tabs = ROLE_TABS.get(role, [])
    if not tabs:
        return

    if "active_tab" not in st.session_state or st.session_state.active_tab not in tabs:
        st.session_state.active_tab = tabs[0]

    # Redesigned profile HTML string (reused across Desktop/Tablet)
    profile_html = f"""
    <div class="desktop-profile-box">
        <div class="desktop-profile-avatar">{initials}</div>
        <div class="desktop-profile-text">
            <div class="desktop-profile-name">{full_name}</div>
            <div class="desktop-profile-role">{role}</div>
        </div>
    </div>
    """

    # Inject redesigned CSS styles
    st.markdown(get_navbar_css(), unsafe_allow_html=True)

    # ==========================================
    # DESKTOP NAVBAR (> 1100px)
    # ==========================================
    desktop_container = st.container()
    with desktop_container:
        st.markdown('<span class="nav-hook desktop-nav-hook"></span>', unsafe_allow_html=True)
        d_brand_col, d_actions_col = st.columns([3, 7])

        with d_brand_col:
            st.markdown('<h3 style="color: #007B8A; margin:0; padding-top:4px; font-weight: 800; font-size: 1.3rem; letter-spacing: -0.5px;">MediFlow <span style="color:#3A9AD9">AI</span></h3>', unsafe_allow_html=True)

        with d_actions_col:
            dp_col0, dp_col1, dp_col2, dp_col3 = st.columns([2, 4.5, 1.5, 2])
            with dp_col1:
                st.markdown(profile_html, unsafe_allow_html=True)
            with dp_col2:
                if st.button("Refresh", key="d_ref", help="Refresh data"):
                    st.rerun()
            with dp_col3:
                render_logout_button(key="d_logout")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        d_tab_cols = st.columns(len(tabs))
        for i, tab in enumerate(tabs):
            with d_tab_cols[i]:
                btn_type = "primary" if st.session_state.active_tab == tab else "secondary"
                if st.button(tab, key=f"d_tab_{tab}", use_container_width=True, type=btn_type):
                    st.session_state.active_tab = tab
                    st.rerun()


    # ==========================================
    # TABLET NAVBAR (768px - 1100px)
    # ==========================================
    tablet_container = st.container()
    with tablet_container:
        st.markdown('<span class="nav-hook tablet-nav-hook"></span>', unsafe_allow_html=True)
        t_brand_col, t_actions_col = st.columns([3, 7])

        with t_brand_col:
            st.markdown('<h3 style="color: #007B8A; margin:0; padding-top:4px; font-weight: 800; font-size: 1.3rem; letter-spacing: -0.5px;">MediFlow <span style="color:#3A9AD9">AI</span></h3>', unsafe_allow_html=True)

        with t_actions_col:
            tp_col0, tp_col1, tp_col2, tp_col3 = st.columns([1, 5.5, 2, 3.5])
            with tp_col1:
                st.markdown(profile_html, unsafe_allow_html=True)
            with tp_col2:
                if st.button("Refresh", key="t_ref", help="Refresh data"):
                    st.rerun()
            with tp_col3:
                render_logout_button(key="t_logout")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
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
        st.markdown('<div style="display:flex; align-items:center; height: 38px;"><h3 style="color: #007B8A; margin:0; font-weight: 800; font-size: 1.25rem; letter-spacing: -0.5px;">MediFlow <span style="color:#3A9AD9">AI</span></h3></div>', unsafe_allow_html=True)

        with st.popover("Menu", use_container_width=False):
                # Smooth close drawer button 
                st.markdown("""
                <div style="display:flex; justify-content:flex-end; margin-bottom: 8px;">
                    <div id="mobile-drawer-close" style="font-weight:bold; font-size:1.3rem; color:var(--neutral-muted); cursor:pointer; padding: 6px 12px; transition: color 0.15s ease;">✕</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Close button JavaScript injector
                import streamlit.components.v1 as components
                components.html("""
                <script>
                setTimeout(() => {
                    const doc = window.parent.document;
                    const popover = doc.querySelector('div[data-testid="stPopoverBody"]');
                    if (!popover) return;
                    
                    const closeBtn = doc.getElementById('mobile-drawer-close');
                    if (closeBtn && !closeBtn.hasAttribute('data-attached')) {
                        closeBtn.setAttribute('data-attached', 'true');
                        closeBtn.addEventListener('click', () => {
                            popover.style.animation = 'drawerSlideOut 0.25s forwards cubic-bezier(0.16, 1, 0.3, 1)';
                            setTimeout(() => {
                                const toggleBtn = doc.querySelector('div[data-testid="stPopover"] > button');
                                if (toggleBtn) {
                                    toggleBtn.click();
                                }
                            }, 240);
                        });
                    }
                    
                    const navBtns = doc.querySelectorAll('div[data-testid="stPopoverBody"] button');
                    navBtns.forEach(btn => {
                        if (!btn.hasAttribute('data-attached')) {
                            btn.setAttribute('data-attached', 'true');
                            btn.addEventListener('click', (e) => {
                                if (!btn.hasAttribute('data-anim-played')) {
                                    e.preventDefault();
                                    e.stopPropagation();
                                    btn.setAttribute('data-anim-played', 'true');
                                    popover.style.animation = 'drawerSlideOut 0.25s forwards cubic-bezier(0.16, 1, 0.3, 1)';
                                    setTimeout(() => {
                                        btn.click();
                                    }, 240);
                                }
                            }, true);
                        }
                    });
                }, 100);
                </script>
                """, height=0, width=0)

                # Modern Mobile Drawer Profile Info Display
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #f8fafc, #f1f5f9); padding: 16px; border-radius: 8px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px; border: 1px solid var(--border-light);">
                    <div style="background: linear-gradient(135deg, #007B8A, #3A9AD9); color: white; border-radius: 50%; width: 38px; height: 38px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; box-shadow: 0 2px 4px rgba(0,123,138,0.25);">{initials}</div>
                    <div style="line-height: 1.3;">
                        <div style="color: var(--neutral-dark); font-size: 0.92rem; font-weight: 700;">{full_name}</div>
                        <div style="color: #007B8A; font-size: 0.72rem; text-transform: uppercase; font-weight: 700; letter-spacing: 0.5px;">{role}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown("<p style='font-weight: 600; font-size: 0.8rem; color: #475569; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;'>Navigation</p>", unsafe_allow_html=True)
                for tab in tabs:
                    btn_type = "primary" if st.session_state.active_tab == tab else "secondary"
                    if st.button(tab, key=f"m_tab_{tab}", use_container_width=True, type=btn_type):
                        st.session_state.active_tab = tab
                        st.rerun()

                st.markdown("<hr style='margin: 16px 0; border: 0; border-top: 1px solid var(--border-light);' />", unsafe_allow_html=True)

                if st.button("Refresh Data", key="m_ref", use_container_width=True):
                    st.rerun()

                render_logout_button(key="m_logout")

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