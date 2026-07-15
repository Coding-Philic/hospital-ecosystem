"""
MediFlow AI — Charts & Analytics Components
=============================================
Plotly-based dashboard charts for admin and management views.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from utils.constants import COLORS


def render_kpi_row(stats: dict):
    """Render a row of KPI metric cards."""
    cols = st.columns(4)

    kpis = [
        ("Total Appointments", stats.get("total_appointments", 0), COLORS["primary"]),
        ("Waiting Patients", stats.get("waiting_patients", 0), COLORS["warning"]),
        ("Completed", stats.get("completed_consultations", 0), COLORS["success"]),
        ("Active Doctors", stats.get("active_doctors", 0), COLORS["accent"]),
    ]

    for col, (label, value, color) in zip(cols, kpis):
        with col:
            st.markdown(f"""
            <div style="
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-top: 3px solid {color};
                border-radius: 4px;
                padding: 1.2rem;
                text-align: center;
            ">
                <div style="font-size: 2rem; font-weight: 800; color: {color};">
                    {value}
                </div>
                <div style="color: var(--text-secondary); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.5px;">
                    {label}
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_kpi_row_extended(stats: dict):
    """Render a second row of KPI cards."""
    cols = st.columns(3)

    kpis = [
        ("Pending Prescriptions", stats.get("pending_prescriptions", 0), COLORS["secondary"]),
        ("Low Stock Items", stats.get("low_stock_items", 0), COLORS["danger"]),
        ("In Progress", stats.get("in_progress", 0), COLORS["info"]),
    ]

    for col, (label, value, color) in zip(cols, kpis):
        with col:
            st.markdown(f"""
            <div style="
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-top: 3px solid {color};
                border-radius: 4px;
                padding: 1.2rem;
                text-align: center;
            ">
                <div style="font-size: 2rem; font-weight: 800; color: {color};">
                    {value}
                </div>
                <div style="color: var(--text-secondary); font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.5px;">
                    {label}
                </div>
            </div>
            """, unsafe_allow_html=True)


def render_department_load_chart(appointments: list):
    """Render a bar chart showing patient load by department."""
    if not appointments:
        st.info("No appointment data available.")
        return

    # Count by department
    dept_counts = {}
    for appt in appointments:
        dept = appt.get("departments", {})
        dept_name = dept.get("name", "Unknown") if isinstance(dept, dict) else "Unknown"
        dept_counts[dept_name] = dept_counts.get(dept_name, 0) + 1

    if not dept_counts:
        st.info("No department data.")
        return

    fig = go.Figure(data=[
        go.Bar(
            x=list(dept_counts.keys()),
            y=list(dept_counts.values()),
            marker=dict(
                color=COLORS["primary"],
            ),
            text=list(dept_counts.values()),
            textposition="auto",
        )
    ])

    fig.update_layout(
        title="Patient Load by Department",
        xaxis_title="Department",
        yaxis_title="Patients",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_primary"], family="Inter"),
        xaxis=dict(tickangle=-45),
        height=400,
    )

    st.plotly_chart(fig, use_container_width=True)


def render_urgency_pie_chart(appointments: list):
    """Render a pie chart showing urgency distribution."""
    if not appointments:
        return

    urgency_counts = {}
    for appt in appointments:
        urgency = appt.get("urgency", "routine")
        urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1

    if not urgency_counts:
        return

    colors = {
        "routine": "#22c55e",
        "semi_urgent": "#f59e0b",
        "urgent": "#ef4444",
        "emergency": "#dc2626",
    }

    fig = go.Figure(data=[go.Pie(
        labels=[k.replace("_", " ").title() for k in urgency_counts.keys()],
        values=list(urgency_counts.values()),
        marker=dict(colors=[colors.get(k, "#94a3b8") for k in urgency_counts.keys()]),
        hole=0.4,
        textinfo="percent+label",
    )])

    fig.update_layout(
        title="Urgency Distribution",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_primary"], family="Inter"),
        height=350,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


def render_status_pie_chart(appointments: list):
    """Render a pie chart showing appointment status distribution."""
    if not appointments:
        return

    status_counts = {}
    for appt in appointments:
        status = appt.get("status", "waiting")
        status_counts[status] = status_counts.get(status, 0) + 1

    colors = {
        "waiting": "#f59e0b",
        "in_progress": COLORS["primary"],
        "completed": "#22c55e",
        "cancelled": "#ef4444",
        "no_show": "#94a3b8",
    }

    fig = go.Figure(data=[go.Pie(
        labels=[k.replace("_", " ").title() for k in status_counts.keys()],
        values=list(status_counts.values()),
        marker=dict(colors=[colors.get(k, "#94a3b8") for k in status_counts.keys()]),
        hole=0.4,
        textinfo="percent+label",
    )])

    fig.update_layout(
        title="Appointment Status",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_primary"], family="Inter"),
        height=350,
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)


def render_doctor_workload_chart(doctors: list):
    """Render a horizontal bar chart showing doctor workload."""
    if not doctors:
        return

    names = []
    tokens = []
    statuses = []
    for doc in doctors:
        user_info = doc.get("users", {}) or {}
        names.append(f"Dr. {user_info.get('full_name', 'Unknown')}")
        tokens.append(doc.get("current_token", 0))
        statuses.append(doc.get("status", "offline"))

    status_colors = {
        "available": "#22c55e",
        "busy": "#ef4444",
        "on_break": "#f59e0b",
        "offline": "#475569",
    }

    fig = go.Figure(data=[go.Bar(
        y=names,
        x=tokens,
        orientation="h",
        marker=dict(
            color=[status_colors.get(s, "#94a3b8") for s in statuses],
        ),
        text=tokens,
        textposition="auto",
    )])

    fig.update_layout(
        title="Doctor Workload (Patients Seen Today)",
        xaxis_title="Patients",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=COLORS["text_primary"], family="Inter"),
        height=max(300, len(names) * 40),
    )

    st.plotly_chart(fig, use_container_width=True)
