"""
MediFlow AI — 🏥 Patient Portal
=================================
Patient-facing dashboard for:
- Symptom submission with AI analysis
- Queue tracking
- Prescription history
- Health profile management
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.auth import require_auth
from components.navbar import render_navbar
from components.patient_intake_form import render_intake_form
from components.intake_chat import render_intake_chat
from components.queue_display import render_queue_card
from components.prescription_form import render_prescription_view
from components.workflow_tracker import render_workflow_tracker
from database.supabase_client import get_current_user
from database import queries as db
from agents.orchestrator import run_intake_pipeline
from agents.workflow_agent import get_workflow_timeline, get_current_state

st.set_page_config(page_title="Patient Portal — MediFlow AI", layout="wide")

# Auth guard
require_auth(allowed_roles=["patient", "admin"])
render_navbar()

profile = get_current_user()
patient = db.get_patient_by_user_id(profile["id"])

st.markdown("# Patient Portal")

# ── Active Tab Logic ────────────────────────────────────────────
active_tab = st.session_state.get("active_tab", "New Visit")

# ══════════════════════════════════════════════════════════════
# TAB 1: New Visit (Symptom Submission)
# ══════════════════════════════════════════════════════════════
if active_tab == "New Visit":
    if not patient:
        st.warning("⚠️ Please complete your intake form first before booking a visit.")
        render_intake_form()
    else:
        # Launch the interactive, multi-modal intake chat
        render_intake_chat(patient)


# ══════════════════════════════════════════════════════════════
# TAB 2: Queue Status
# ══════════════════════════════════════════════════════════════
elif active_tab == "My Queue":
    st.markdown("### My Active Queue Tokens")

    if not patient:
        st.info("Complete your intake form to start booking appointments.")
    else:
        try:
            appointments = db.get_appointments_by_patient(patient["id"])
            active = [a for a in appointments if a.get("status") in ("waiting", "in_progress")]

            if active:
                for appt in active:
                    doctor_info = appt.get("doctors", {}) or {}
                    doc_user = doctor_info.get("users", {}) or {}
                    dept_info = appt.get("departments", {}) or {}

                    render_queue_card({
                        "token_number": appt.get("token_number", "N/A"),
                        "queue_position": appt.get("queue_position", 0),
                        "estimated_wait": "Calculating...",
                        "department": dept_info.get("name", "N/A"),
                        "doctor_name": doc_user.get("full_name", "Doctor"),
                        "status": appt.get("status", "waiting"),
                        "urgency": appt.get("urgency", "routine"),
                    })

                    # Workflow tracker
                    try:
                        current = get_current_state(appt["id"])
                        timeline = get_workflow_timeline(appt["id"])
                        render_workflow_tracker(current, timeline)
                    except Exception:
                        pass
            else:
                st.info("No active queue tokens. Start a new visit to get one!")
        except Exception as e:
            st.error(f"Error loading queue: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 3: Prescriptions
# ══════════════════════════════════════════════════════════════
elif active_tab == "Prescriptions":
    st.markdown("### My Prescriptions")

    if not patient:
        st.info("Complete your intake form first.")
    else:
        try:
            prescriptions = db.get_prescriptions_by_patient(patient["id"])
            if prescriptions:
                for rx in prescriptions:
                    render_prescription_view(rx)
            else:
                st.info("No prescriptions yet. They'll appear here after your consultation.")
        except Exception as e:
            st.error(f"Error loading prescriptions: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 4: Visit History
# ══════════════════════════════════════════════════════════════
elif active_tab == "Visit History":
    st.markdown("### Visit History")

    if not patient:
        st.info("No visit history.")
    else:
        try:
            consultations = db.get_consultations_by_patient(patient["id"])
            if consultations:
                for consult in consultations:
                    doc_info = consult.get("doctors", {}) or {}
                    doc_user = doc_info.get("users", {}) or {}

                    with st.expander(f"{consult.get('created_at', 'N/A')[:10]} — Dr. {doc_user.get('full_name', 'Unknown')}"):
                        if consult.get("symptoms"):
                            st.markdown(f"**Symptoms:** {consult['symptoms']}")
                        if consult.get("diagnosis"):
                            st.markdown(f"**Diagnosis:** {consult['diagnosis']}")
                        if consult.get("examination_notes"):
                            st.markdown(f"**Notes:** {consult['examination_notes']}")
                        if consult.get("follow_up_date"):
                            st.markdown(f"**Follow-up:** {consult['follow_up_date']}")
                        if consult.get("vitals"):
                            st.markdown("**Vitals:**")
                            vitals = consult["vitals"]
                            cols = st.columns(3)
                            for i, (k, v) in enumerate(vitals.items()):
                                cols[i % 3].metric(k.replace("_", " ").title(), v)
            else:
                st.info("No consultation history yet.")
        except Exception as e:
            st.error(f"Error loading history: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 5: Profile
# ══════════════════════════════════════════════════════════════
elif active_tab == "My Profile":
    st.markdown("### My Health Profile")
    render_intake_form()
