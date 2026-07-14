"""
MediFlow AI — 📊 Admin Dashboard
===================================
Admin/management overview dashboard for:
- Hospital-wide analytics
- Doctor utilization
- User management
- Department management
- Audit trail
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.auth import require_auth
from components.navbar import render_navbar
from components.charts import (
    render_kpi_row, render_kpi_row_extended,
    render_department_load_chart, render_urgency_pie_chart,
    render_status_pie_chart, render_doctor_workload_chart,
)
from components.queue_display import render_metric_card
from database.supabase_client import get_current_user
from database import queries as db
from config import config

st.set_page_config(page_title="Admin — MediFlow AI", layout="wide")

require_auth(allowed_roles=["admin"])
render_navbar()

profile = get_current_user()

st.markdown("# 📊 Admin Dashboard")
st.markdown("Hospital-wide analytics and management panel.")

# ── Active Tab Logic ────────────────────────────────────────────
active_tab = st.session_state.get("active_tab", "Analytics")

# ══════════════════════════════════════════════════════════════
# TAB 1: Analytics
# ══════════════════════════════════════════════════════════════
if active_tab == "Analytics":
    st.markdown("### 📊 Today's Hospital Analytics")

    try:
        stats = db.get_today_stats()

        # KPI Row
        render_kpi_row(stats)
        st.markdown("")
        render_kpi_row_extended(stats)

        st.markdown("---")

        # Charts
        today_appts = db.get_today_appointments()

        if today_appts:
            col1, col2 = st.columns(2)
            with col1:
                render_department_load_chart(today_appts)
            with col2:
                render_urgency_pie_chart(today_appts)

            col3, col4 = st.columns(2)
            with col3:
                render_status_pie_chart(today_appts)
            with col4:
                doctors = db.get_all_doctors()
                render_doctor_workload_chart(doctors)
        else:
            st.info("No appointment data available for today. Charts will appear when patients are registered.")

    except Exception as e:
        st.error(f"Error loading analytics: {e}")

    if st.button("🔄 Refresh Analytics"):
        st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB 2: Doctors
# ══════════════════════════════════════════════════════════════
elif active_tab == "Doctors":
    st.markdown("### 🩺 Doctor Management")

    try:
        doctors = db.get_all_doctors()
        departments = db.get_all_departments()

        if doctors:
            status_icons = {"available": "🟢", "busy": "🔴", "on_break": "🟡", "offline": "⚫"}

            for doc in doctors:
                user_info = doc.get("users", {}) or {}
                dept_info = doc.get("departments", {}) or {}
                status = doc.get("status", "offline")

                col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
                with col1:
                    st.markdown(f"**Dr. {user_info.get('full_name', 'Unknown')}**")
                    st.caption(f"{doc.get('specialization', 'N/A')} | {doc.get('qualification', 'N/A')}")
                with col2:
                    st.markdown(f"🏥 {dept_info.get('name', 'N/A')}")
                    st.caption(f"Exp: {doc.get('experience_years', 0)} yrs | Fee: ₹{doc.get('consultation_fee', 0)}")
                with col3:
                    st.markdown(f"{status_icons.get(status, '⚪')} {status.title()}")
                with col4:
                    st.markdown(f"Patients: {doc.get('current_token', 0)}/{doc.get('max_daily_patients', 30)}")

                st.markdown("---")
        else:
            st.info("No doctors registered yet.")

        # Add new doctor
        with st.expander("➕ Register New Doctor"):
            with st.form("add_doctor_form"):
                # First, get users with doctor role who don't have a doctor record yet
                doctor_users = db.get_users_by_role("doctor")
                existing_doctor_user_ids = [d.get("user_id") for d in doctors]
                available_users = [u for u in doctor_users if u["id"] not in existing_doctor_user_ids]

                if available_users:
                    selected_user = st.selectbox(
                        "Select User",
                        options=available_users,
                        format_func=lambda u: f"{u['full_name']} ({u['email']})",
                    )
                else:
                    st.warning("No unassigned doctor users found. Create a user with 'doctor' role first.")
                    selected_user = None

                dept_select = st.selectbox(
                    "Department",
                    options=departments,
                    format_func=lambda d: d["name"],
                )
                specialization = st.text_input("Specialization")
                qualification = st.text_input("Qualification")
                experience = st.number_input("Experience (years)", min_value=0, value=5)
                license_no = st.text_input("License Number")
                fee = st.number_input("Consultation Fee (₹)", min_value=0, value=500)
                max_patients = st.number_input("Max Daily Patients", min_value=1, value=30)

                if st.form_submit_button("📝 Register Doctor", use_container_width=True, type="primary"):
                    if selected_user and dept_select:
                        db.create_doctor({
                            "user_id": selected_user["id"],
                            "department_id": dept_select["id"],
                            "specialization": specialization,
                            "qualification": qualification,
                            "experience_years": experience,
                            "license_number": license_no,
                            "consultation_fee": fee,
                            "max_daily_patients": max_patients,
                        })
                        st.success(f"✅ Dr. {selected_user['full_name']} registered!")
                        st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 3: Users
# ══════════════════════════════════════════════════════════════
elif active_tab == "Users":
    st.markdown("### 👥 User Management")

    try:
        all_users = db.get_all_users()

        # Stats by role
        role_counts = {}
        for u in all_users:
            role = u.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1

        cols = st.columns(5)
        role_icons = {"patient": "🏥", "doctor": "🩺", "receptionist": "👩‍⚕️", "pharmacist": "💊", "admin": "📊"}
        for col, role in zip(cols, config.USER_ROLES):
            with col:
                render_metric_card(
                    role.title(),
                    role_counts.get(role, 0),
                    role_icons.get(role, "👤"),
                    "#6366f1",
                )

        st.markdown("---")

        # Filter
        role_filter = st.selectbox(
            "Filter by Role",
            ["All"] + config.USER_ROLES,
            key="user_role_filter",
        )

        # User list
        for u in all_users:
            if role_filter != "All" and u.get("role") != role_filter:
                continue

            icon = role_icons.get(u.get("role", ""), "👤")
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            with col1:
                st.markdown(f"{icon} **{u.get('full_name', 'Unknown')}**")
                st.caption(u.get("email", ""))
            with col2:
                st.markdown(f"Phone: {u.get('phone', 'N/A')}")
            with col3:
                st.markdown(f"`{u.get('role', 'N/A')}`")
            with col4:
                active = u.get("is_active", True)
                st.markdown(f"{'🟢 Active' if active else '🔴 Inactive'}")
            st.markdown("---")

    except Exception as e:
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 4: Departments
# ══════════════════════════════════════════════════════════════
elif active_tab == "Departments":
    st.markdown("### 🏥 Department Management")

    try:
        departments = db.get_all_departments()

        for dept in departments:
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.markdown(f"**{dept['name']}**")
                st.caption(dept.get("description", "No description"))
            with col2:
                st.markdown(f"Floor: {dept.get('floor_number', 'N/A')}")
            with col3:
                st.markdown(f"{'🟢 Active' if dept.get('is_active') else '🔴 Inactive'}")
            st.markdown("---")

    except Exception as e:
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 5: Audit Trail
# ══════════════════════════════════════════════════════════════
elif active_tab == "Audit Trail":
    st.markdown("### 📜 Audit Trail")
    st.info("Complete log of all system actions, AI decisions, and human overrides.")

    # Filter
    entity_filter = st.selectbox(
        "Filter by Entity",
        ["All", "appointment", "prescription", "prescription_item", "workflow"],
        key="audit_filter",
    )

    try:
        entity_type = entity_filter if entity_filter != "All" else None
        audit_entries = db.get_audit_log(limit=100, entity_type=entity_type)

        if audit_entries:
            for entry in audit_entries:
                user_info = entry.get("users", {}) or {}
                actor_name = user_info.get("full_name", "System")
                was_override = entry.get("was_overridden", False)
                override_icon = "⚠️ OVERRIDE" if was_override else ""

                action_icons = {
                    "ai_triage": "🧠",
                    "queue_token_assigned": "🎫",
                    "override_department": "⚠️",
                    "prescription_created": "📝",
                    "prescription_dispensed": "💊",
                    "substitute_approved": "🔄",
                    "workflow_transition": "📊",
                }
                icon = action_icons.get(entry.get("action", ""), "📌")

                st.markdown(f"""
                {icon} **{entry.get('action', 'N/A').replace('_', ' ').title()}** {override_icon}
                <br/><span style="color: var(--text-secondary); font-size: 0.85rem;">
                    {entry.get('created_at', 'N/A')[:19]} | By: {actor_name}
                    ({entry.get('actor_role', 'N/A')})
                    | Entity: {entry.get('entity_type', 'N/A')}
                    {f' | Model: {entry["ai_model_used"]}' if entry.get("ai_model_used") else ''}
                    {f' | Confidence: {float(entry["ai_confidence"]):.0%}' if entry.get("ai_confidence") else ''}
                </span>
                """, unsafe_allow_html=True)

                if entry.get("details"):
                    with st.expander("Details", expanded=False):
                        st.json(entry["details"])

                if was_override and entry.get("override_reason"):
                    st.warning(f"Override reason: {entry['override_reason']}")

                st.markdown("---")
        else:
            st.info("No audit entries yet.")

    except Exception as e:
        st.error(f"Error loading audit trail: {e}")
