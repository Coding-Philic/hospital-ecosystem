"""
MediFlow AI — Workflow Tracker Component
==========================================
Visual step-by-step workflow progress bar with timestamps.
"""

import streamlit as st
from utils.constants import WORKFLOW_DISPLAY, COLORS
from config import config


def render_workflow_tracker(current_state: str, workflow_history: list = None):
    """
    Render a visual workflow progress tracker.

    Args:
        current_state: The current workflow state
        workflow_history: List of workflow state transitions (optional, for timestamps)
    """
    states = config.WORKFLOW_STATES
    current_index = states.index(current_state) if current_state in states else -1

    # Build history lookup
    history_map = {}
    if workflow_history:
        for entry in workflow_history:
            history_map[entry.get("state", entry.get("current_state"))] = entry

    # Render progress bar
    st.markdown("""
    <style>
    .workflow-tracker {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        padding: 1rem 0;
    }
    .workflow-step {
        flex: 1;
        min-width: 80px;
        text-align: center;
        padding: 0.5rem 0.3rem;
        border-radius: 8px;
        font-size: 0.72rem;
        transition: all 0.3s ease;
        position: relative;
    }
    .workflow-step.completed {
        background: rgba(34, 197, 94, 0.15);
        border: 1px solid rgba(34, 197, 94, 0.3);
        color: #22c55e;
    }
    .workflow-step.current {
        background: rgba(99, 102, 241, 0.2);
        border: 2px solid #6366f1;
        color: #818cf8;
        font-weight: 700;
        box-shadow: 0 0 15px rgba(99, 102, 241, 0.3);
    }
    .workflow-step.pending {
        background: rgba(148, 163, 184, 0.08);
        border: 1px solid rgba(148, 163, 184, 0.15);
        color: #475569;
    }
    .workflow-step .icon { font-size: 1.2rem; }
    .workflow-step .label { margin-top: 2px; }
    </style>
    """, unsafe_allow_html=True)

    # Build HTML
    steps_html = '<div class="workflow-tracker">'
    for i, state in enumerate(states):
        display = WORKFLOW_DISPLAY.get(state, {"icon": "❓", "label": state, "color": "#94a3b8"})

        if i < current_index:
            css_class = "completed"
        elif i == current_index:
            css_class = "current"
        else:
            css_class = "pending"

        steps_html += f"""<div class="workflow-step {css_class}"><div class="icon">{display['icon']}</div><div class="label">{display['label']}</div></div>"""

    steps_html += '</div>'
    st.markdown(steps_html, unsafe_allow_html=True)

    # Show timeline details if history available
    if workflow_history:
        with st.expander("📜 View Detailed Timeline"):
            for entry in reversed(workflow_history):
                state = entry.get("state", entry.get("current_state", "unknown"))
                display = WORKFLOW_DISPLAY.get(state, {"icon": "❓", "label": state})
                timestamp = entry.get("timestamp", entry.get("created_at", ""))
                by = entry.get("transitioned_by", "System")
                notes = entry.get("notes", "")

                # Format timestamp
                if timestamp:
                    try:
                        from datetime import datetime
                        if isinstance(timestamp, str):
                            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                            time_str = dt.strftime("%I:%M %p")
                            date_str = dt.strftime("%d %b %Y")
                        else:
                            time_str = str(timestamp)
                            date_str = ""
                    except Exception:
                        time_str = str(timestamp)[:19]
                        date_str = ""
                else:
                    time_str = ""
                    date_str = ""

                st.markdown(f"""
                **{display['icon']} {display['label']}** — {time_str}
                <br/><span style="color: #94a3b8; font-size: 0.8rem;">
                    {date_str} • By: {by}
                    {f' • Note: {notes}' if notes else ''}
                </span>
                """, unsafe_allow_html=True)
                st.markdown("---")


def render_mini_status(current_state: str):
    """Render a compact workflow status badge."""
    display = WORKFLOW_DISPLAY.get(current_state, {"icon": "❓", "label": current_state, "color": "#94a3b8"})

    st.markdown(f"""
    <span style="
        background: {display['color']}20;
        color: {display['color']};
        padding: 4px 14px;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.85rem;
    ">
        {display['icon']} {display['label']}
    </span>
    """, unsafe_allow_html=True)
