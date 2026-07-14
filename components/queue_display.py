"""
MediFlow AI — Queue Display Component
=======================================
Real-time queue position card, estimated wait time, and department queue view.
"""

import streamlit as st
from utils.constants import COLORS, WORKFLOW_DISPLAY


def render_queue_card(queue_info: dict):
    """
    Render a queue status card for a patient.

    Args:
        queue_info: dict with token_number, queue_position, estimated_wait,
                   department, doctor_name, status, urgency
    """
    urgency = queue_info.get("urgency", "routine")
    urgency_colors = {
        "routine": "#22c55e",
        "semi_urgent": "#f59e0b",
        "urgent": "#ef4444",
        "emergency": "#dc2626",
    }
    border_color = urgency_colors.get(urgency, "#6366f1")

    status = queue_info.get("status", "waiting")
    status_labels = {
        "waiting": "⏳ Waiting",
        "in_progress": "🩺 In Progress",
        "completed": "✅ Completed",
        "cancelled": "❌ Cancelled",
    }

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid {border_color}40;
        border-left: 4px solid {border_color};
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
                <div style="font-size: 0.85rem; color: #94a3b8;">Token Number</div>
                <div style="font-size: 1.8rem; font-weight: 800; color: #f8fafc; letter-spacing: 2px;">
                    🎫 {queue_info.get('token_number', 'N/A')}
                </div>
            </div>
            <div style="
                background: {border_color}20;
                color: {border_color};
                padding: 4px 16px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 0.85rem;
            ">
                {urgency.replace('_', ' ').title()}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Position in Queue</div>
                <div style="color: #f8fafc; font-size: 1.3rem; font-weight: 700;">
                    #{queue_info.get('queue_position', '?')}
                </div>
            </div>
            <div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Estimated Wait</div>
                <div style="color: {COLORS['accent']}; font-size: 1.3rem; font-weight: 700;">
                    {queue_info.get('estimated_wait', 'N/A')}
                </div>
            </div>
            <div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Department</div>
                <div style="color: #f8fafc; font-size: 0.95rem; font-weight: 600;">
                    {queue_info.get('department', 'Unknown')}
                </div>
            </div>
            <div>
                <div style="color: #94a3b8; font-size: 0.8rem;">Doctor</div>
                <div style="color: #f8fafc; font-size: 0.95rem; font-weight: 600;">
                    Dr. {queue_info.get('doctor_name', 'Unknown')}
                </div>
            </div>
        </div>
        <div style="margin-top: 1rem; text-align: center;">
            <div style="
                display: inline-block;
                background: {COLORS['primary']}20;
                color: {COLORS['primary']};
                padding: 6px 20px;
                border-radius: 20px;
                font-size: 0.9rem;
                font-weight: 600;
            ">
                {status_labels.get(status, status)}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_department_queue(appointments: list, department_name: str = "All"):
    """
    Render a queue list for a department (used by reception dashboard).
    """
    st.markdown(f"#### 📋 Queue — {department_name}")

    if not appointments:
        st.info("No patients in queue.")
        return

    for i, appt in enumerate(appointments):
        patient_info = appt.get("patients", {}) or {}
        user_info = patient_info.get("users", {}) or {}
        doctor_info = appt.get("doctors", {}) or {}
        doc_user = doctor_info.get("users", {}) or {}
        dept_info = appt.get("departments", {}) or {}

        urgency = appt.get("urgency", "routine")
        urgency_color = {"routine": "🟢", "semi_urgent": "🟡", "urgent": "🔴", "emergency": "🚨"}.get(urgency, "⚪")
        status = appt.get("status", "waiting")

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
            col1.markdown(f"**{appt.get('token_number', 'N/A')}**")
            col2.markdown(f"{user_info.get('full_name', 'Unknown')}")
            col3.markdown(f"{dept_info.get('name', 'N/A')}")
            col4.markdown(f"Dr. {doc_user.get('full_name', 'N/A')}")
            col5.markdown(f"{urgency_color} {status.title()}")
            st.markdown("---")


def render_metric_card(label: str, value, icon: str = "📊", color: str = None):
    """Render a styled metric card."""
    bg_color = color or COLORS["primary"]
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {bg_color}15, {bg_color}05);
        border: 1px solid {bg_color}30;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    ">
        <div style="font-size: 1.5rem;">{icon}</div>
        <div style="font-size: 1.8rem; font-weight: 800; color: {bg_color}; margin: 0.3rem 0;">
            {value}
        </div>
        <div style="color: {COLORS['text_secondary']}; font-size: 0.85rem;">
            {label}
        </div>
    </div>
    """, unsafe_allow_html=True)
