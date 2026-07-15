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
    border_color = urgency_colors.get(urgency, COLORS["primary"])

    status = queue_info.get("status", "waiting")
    status_labels = {
        "waiting": "Waiting",
        "in_progress": "In Progress",
        "completed": "Completed",
        "cancelled": "Cancelled",
    }

    st.markdown(f"""
    <div style="
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-left: 4px solid {border_color};
        border-radius: 6px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
            <div>
                <div style="font-size: 0.8rem; color: var(--text-secondary);">Token Number</div>
                <div style="font-size: 1.6rem; font-weight: 800; color: var(--text-primary); letter-spacing: 2px;">
                    {queue_info.get('token_number', 'N/A')}
                </div>
            </div>
            <div style="
                background: {border_color}18;
                color: {border_color};
                padding: 4px 14px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 0.8rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            ">
                {urgency.replace('_', ' ').title()}
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;">
            <div>
                <div style="color: var(--text-secondary); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Position</div>
                <div style="color: var(--text-primary); font-size: 1.2rem; font-weight: 700;">
                    #{queue_info.get('queue_position', '?')}
                </div>
            </div>
            <div>
                <div style="color: var(--text-secondary); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Wait Time</div>
                <div style="color: {COLORS['primary']}; font-size: 1.2rem; font-weight: 700;">
                    {queue_info.get('estimated_wait', 'N/A')}
                </div>
            </div>
            <div>
                <div style="color: var(--text-secondary); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Department</div>
                <div style="color: var(--text-primary); font-size: 0.9rem; font-weight: 600;">
                    {queue_info.get('department', 'Unknown')}
                </div>
            </div>
            <div>
                <div style="color: var(--text-secondary); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.5px;">Doctor</div>
                <div style="color: var(--text-primary); font-size: 0.9rem; font-weight: 600;">
                    Dr. {queue_info.get('doctor_name', 'Unknown')}
                </div>
            </div>
        </div>
        <div style="margin-top: 1rem; text-align: center;">
            <div style="
                display: inline-block;
                background: {COLORS['primary']}15;
                color: {COLORS['primary']};
                padding: 4px 16px;
                border-radius: 4px;
                font-size: 0.85rem;
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
    st.markdown(f"#### Queue — {department_name}")

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
        urgency_label = {"routine": "Routine", "semi_urgent": "Semi-Urgent", "urgent": "Urgent", "emergency": "EMERGENCY"}.get(urgency, urgency)
        status = appt.get("status", "waiting")

        with st.container():
            col1, col2, col3, col4, col5 = st.columns([1, 2, 2, 2, 1])
            col1.markdown(f"**{appt.get('token_number', 'N/A')}**")
            col2.markdown(f"{user_info.get('full_name', 'Unknown')}")
            col3.markdown(f"{dept_info.get('name', 'N/A')}")
            col4.markdown(f"Dr. {doc_user.get('full_name', 'N/A')}")
            col5.markdown(f"{urgency_label} | {status.title()}")
            st.markdown("---")


def render_metric_card(label: str, value, icon: str = "", color: str = None):
    """Render a styled metric card."""
    bg_color = color or COLORS["primary"]
    st.markdown(f"""
    <div style="
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-top: 3px solid {bg_color};
        border-radius: 4px;
        padding: 1.2rem;
        text-align: center;
    ">
        <div style="font-size: 1.8rem; font-weight: 800; color: {bg_color}; margin: 0.3rem 0;">
            {value}
        </div>
        <div style="color: var(--text-secondary); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.5px;">
            {label}
        </div>
    </div>
    """, unsafe_allow_html=True)
