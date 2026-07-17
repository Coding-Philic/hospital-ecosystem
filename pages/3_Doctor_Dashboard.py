"""
MediFlow AI — Doctor Dashboard
====================================
Doctor-facing dashboard for:
- Pre-triaged patient queue with symptom summary
- Patient history viewer
- Consultation recording (diagnosis, examination, vitals)
- Structured prescription entry
- Availability status toggle
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import date
from components.auth import require_auth
from components.navbar import render_navbar
from components.prescription_form import render_prescription_form
from components.workflow_tracker import render_mini_status
from database.supabase_client import get_current_user
from database import queries as db
from agents.orchestrator import run_prescription_pipeline
from agents.workflow_agent import transition_state
from utils.constants import INVESTIGATION_TYPES

st.set_page_config(page_title="Doctor Dashboard — MediFlow AI", layout="wide")

require_auth(allowed_roles=["doctor", "admin"])
render_navbar()

profile = get_current_user()

# Get doctor record
doctor = db.get_doctor_by_user_id(profile["id"])

st.markdown("# Doctor Dashboard")

if not doctor:
    st.warning("Your doctor profile hasn't been set up yet. Please contact an admin.")
    st.stop()

# Doctor status display
st.markdown(f"**Status:** {doctor['status'].replace('_', ' ').title()}")

# ── Active Tab Logic ────────────────────────────────────────────
active_tab = st.session_state.get("active_tab", "Patient Queue")

# ══════════════════════════════════════════════════════════════
# TAB 1: Patient Queue
# ══════════════════════════════════════════════════════════════
if active_tab == "Patient Queue":
    st.markdown("### Today's Patient Queue")

    try:
        today = date.today().isoformat()
        appointments = db.get_appointments_by_doctor(doctor["id"], date_filter=today)

        waiting = [a for a in appointments if a.get("status") == "waiting"]
        in_progress = [a for a in appointments if a.get("status") == "in_progress"]
        completed = [a for a in appointments if a.get("status") == "completed"]

        # Stats
        col1, col2, col3 = st.columns(3)
        col1.metric("Waiting", len(waiting))
        col2.metric("In Progress", len(in_progress))
        col3.metric("Completed", len(completed))

        st.markdown("---")

        # Current patient in progress
        if in_progress:
            st.markdown("#### Current Patient")
            appt = in_progress[0]
            p_info = appt.get("patients", {}) or {}
            p_user = p_info.get("users", {}) or {}

            st.markdown(f"""
            <div style="
                background: var(--card-bg);
                border: 1px solid var(--border-color);
                border-left: 4px solid var(--accent);
                border-radius: 6px;
                padding: 1.2rem;
                margin-bottom: 1rem;
            ">
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--accent);">
                    {appt.get('token_number', 'N/A')} — {p_user.get('full_name', 'Unknown')}
                </div>
                <div style="color: var(--text-secondary); margin-top: 0.3rem;">
                    {appt.get('symptom_summary', 'No symptoms recorded')[:200]}
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.info(f"Patient phone: {p_user.get('phone', 'N/A')}")

        st.markdown("---")

        # Waiting queue
        if waiting:
            st.markdown("#### Waiting Patients")
            for appt in waiting:
                p_info = appt.get("patients", {}) or {}
                p_user = p_info.get("users", {}) or {}

                urgency_label = {"routine": "Routine", "semi_urgent": "Semi-Urgent", "urgent": "Urgent", "emergency": "EMERGENCY"}.get(
                    appt.get("urgency", "routine"), "Routine"
                )

                col1, col2, col3 = st.columns([1, 3, 2])
                with col1:
                    st.markdown(f"**{appt.get('token_number', 'N/A')}** <br/><span style='font-size:0.8rem;color:var(--text-secondary)'>{urgency_label}</span>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"**{p_user.get('full_name', 'Unknown')}**")
                    st.caption(f"{appt.get('symptom_summary', 'No symptoms')[:100]}")
                with col3:
                    if st.button("Start Consultation", key=f"start_{appt['id']}", type="primary"):
                        # Update appointment status
                        db.update_appointment(appt["id"], {
                            "status": "in_progress",
                            "consultation_start_time": date.today().isoformat(),
                        })
                        # Update doctor status
                        db.update_doctor_status(doctor["id"], "busy")
                        # Transition workflow
                        try:
                            transition_state(
                                appt["id"], appt["patient_id"],
                                "in_consultation", profile["id"], "doctor",
                                "Consultation started",
                            )
                        except Exception:
                            pass
                        st.success(f"Started consultation with {p_user.get('full_name', 'patient')}")
                        st.rerun()

                st.markdown("---")
        else:
            st.success("No patients waiting.")

    except Exception as e:
        st.error(f"Error loading queue: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 2: Consultation (Diagnosis & Notes)
# ══════════════════════════════════════════════════════════════
elif active_tab == "Consultation":
    st.markdown("### Patient Consultation")

    try:
        today = date.today().isoformat()
        appointments = db.get_appointments_by_doctor(doctor["id"], date_filter=today, status="in_progress")

        if not appointments:
            st.info("No active consultation. Start one from the Patient Queue tab.")
        else:
            appt = appointments[0]
            p_info = appt.get("patients", {}) or {}
            p_user = p_info.get("users", {}) or {}

            st.markdown(f"#### Patient: {p_user.get('full_name', 'Unknown')} | Token: {appt.get('token_number', 'N/A')}")

            # Patient info card
            if p_info:
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**ID:** {p_info.get('patient_id_code', 'N/A')}")
                col2.markdown(f"**Blood Group:** {p_info.get('blood_group', 'N/A')}")
                col3.markdown(f"**Allergies:** {', '.join(p_info.get('allergies') or []) or 'None'}")

            # AI Triage Summary Card
            triage_summary = appt.get("symptom_summary", "")
            if triage_summary:
                st.markdown("""
                <div style="background: var(--card-bg); border-left: 4px solid var(--accent); padding: 1rem; border-radius: 4px; margin-bottom: 1.5rem; border-top: 1px solid var(--border-color); border-right: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color);">
                    <div style="font-weight: 700; color: var(--accent); margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                        AI Triage Report
                    </div>
                    <div style="color: var(--text-primary); font-size: 0.95rem; white-space: pre-wrap;">
                        {}
                    </div>
                </div>
                """.format(triage_summary.replace('\n', '<br>')), unsafe_allow_html=True)

            # Check for existing consultation
            existing_consult = db.get_consultation_by_appointment(appt["id"])

            # Handle AI generated notes safely before widget instantiation
            if "temp_ai_notes" in st.session_state:
                ai_notes = st.session_state.pop("temp_ai_notes")
                st.session_state.consult_symptoms = ai_notes.get("symptoms", "")
                st.session_state.consult_exam = ai_notes.get("examination_notes", "")
                st.session_state.consult_diagnosis = ai_notes.get("diagnosis", "")
                st.session_state.consult_additional = ai_notes.get("additional_notes", "")

            with st.form("consultation_form"):
                st.markdown("##### Vitals")
                vcol1, vcol2, vcol3 = st.columns(3)
                with vcol1:
                    bp = st.text_input("Blood Pressure", placeholder="120/80", key="vital_bp",
                                       value=existing_consult.get("vitals", {}).get("bp", "") if existing_consult else "")
                    temp = st.text_input("Temperature (°F)", placeholder="98.6", key="vital_temp",
                                        value=existing_consult.get("vitals", {}).get("temperature", "") if existing_consult else "")
                with vcol2:
                    pulse = st.text_input("Pulse (bpm)", placeholder="72", key="vital_pulse",
                                         value=existing_consult.get("vitals", {}).get("pulse", "") if existing_consult else "")
                    spo2 = st.text_input("SpO2 (%)", placeholder="98", key="vital_spo2",
                                        value=existing_consult.get("vitals", {}).get("spo2", "") if existing_consult else "")
                with vcol3:
                    weight = st.text_input("Weight (kg)", placeholder="70", key="vital_weight",
                                          value=existing_consult.get("vitals", {}).get("weight", "") if existing_consult else "")
                    height = st.text_input("Height (cm)", placeholder="170", key="vital_height",
                                          value=existing_consult.get("vitals", {}).get("height", "") if existing_consult else "")

                st.markdown("##### Clinical Notes")
                symptoms = st.text_area("Symptoms / Chief Complaint", height=80, key="consult_symptoms",
                                       value=existing_consult.get("symptoms", appt.get("symptom_summary", "")) if existing_consult else appt.get("symptom_summary", ""))
                examination = st.text_area("Examination Notes", height=100, key="consult_exam",
                                          value=existing_consult.get("examination_notes", "") if existing_consult else "")
                diagnosis = st.text_input("Diagnosis", key="consult_diagnosis",
                                         value=existing_consult.get("diagnosis", "") if existing_consult else "")
                additional = st.text_area("Additional Notes", height=60, key="consult_additional",
                                         value=existing_consult.get("additional_notes", "") if existing_consult else "")

                st.markdown("##### Follow-up")
                follow_up = st.date_input("Follow-up Date (optional)", value=None, key="consult_followup")
                follow_notes = st.text_input("Follow-up Instructions", key="consult_followup_notes",
                                            value=existing_consult.get("follow_up_notes", "") if existing_consult else "")

                col_sub1, col_sub2 = st.columns(2)
                with col_sub1:
                    save_clicked = st.form_submit_button("Save Consultation", use_container_width=True, type="primary")
                with col_sub2:
                    auto_fill_clicked = st.form_submit_button("✨ AI Auto-Fill Clinical Notes", use_container_width=True)

                vitals = {
                    "bp": bp, "temperature": temp, "pulse": pulse,
                    "spo2": spo2, "weight": weight, "height": height,
                }
                vitals = {k: v for k, v in vitals.items() if v}

                if auto_fill_clicked:
                    with st.spinner("AI is generating clinical notes..."):
                        from agents.symptom_classifier import generate_clinical_notes_from_triage
                        notes = generate_clinical_notes_from_triage(triage_summary, vitals, p_info)
                        if notes:
                            st.session_state.temp_ai_notes = notes
                            st.rerun()
                        else:
                            st.error("AI Generation failed! Please check your API key and connection.")

                if save_clicked:
                    consult_data = {
                        "appointment_id": appt["id"],
                        "patient_id": appt["patient_id"],
                        "doctor_id": doctor["id"],
                        "symptoms": symptoms,
                        "examination_notes": examination,
                        "diagnosis": diagnosis,
                        "additional_notes": additional,
                        "vitals": vitals,
                        "follow_up_date": follow_up.isoformat() if follow_up else None,
                        "follow_up_notes": follow_notes,
                    }

                    if existing_consult:
                        db.update_consultation(existing_consult["id"], consult_data)
                        st.success("Consultation updated.")
                    else:
                        db.create_consultation(consult_data)
                        st.success("Consultation saved.")

            # Complete consultation button
            st.markdown("---")
            if st.button("Complete Consultation & Discharge", use_container_width=True):
                db.update_appointment(appt["id"], {"status": "completed"})
                db.update_doctor_status(doctor["id"], "available")
                try:
                    transition_state(
                        appt["id"], appt["patient_id"],
                        "discharged", profile["id"], "doctor",
                        "Consultation completed",
                    )
                except Exception:
                    pass
                st.success("Patient discharged.")
                st.rerun()

    except Exception as e:
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 3: Write Prescription
# ══════════════════════════════════════════════════════════════
elif active_tab == "Prescribe":
    st.markdown("### Write Prescription")

    try:
        today = date.today().isoformat()
        appointments = db.get_appointments_by_doctor(doctor["id"], date_filter=today, status="in_progress")

        if not appointments:
            st.info("Start a consultation first to write a prescription.")
        else:
            appt = appointments[0]
            p_info = appt.get("patients", {}) or {}
            p_user = p_info.get("users", {}) or {}

            # Check for existing consultation
            consult = db.get_consultation_by_appointment(appt["id"])
            if not consult:
                st.warning("Please save the consultation first before writing a prescription.")
            else:
                st.markdown(f"**Patient:** {p_user.get('full_name', 'Unknown')} | **Diagnosis:** {consult.get('diagnosis', 'N/A')}")

                def handle_prescription_submit(items):
                    """Callback when prescription is submitted."""
                    with st.spinner("Processing prescription through AI pipeline..."):
                        result = run_prescription_pipeline(
                            consultation_id=consult["id"],
                            patient_id=appt["patient_id"],
                            doctor_id=doctor["id"],
                            doctor_user_id=profile["id"],
                            prescription_items=items,
                            patient_allergies=p_info.get("allergies") or [],
                            patient_conditions=p_info.get("chronic_conditions") or [],
                        )

                    rx_result = result.get("prescription", {})
                    pharmacy_result = result.get("pharmacy", {})

                    if rx_result.get("success"):
                        st.success(f"{rx_result.get('message', 'Prescription created!')}")
                        
                        # Clear form only on success
                        st.session_state.prescription_items = []

                        # Pharmacy results
                        if pharmacy_result:
                            if pharmacy_result.get("all_in_stock"):
                                st.success("All medicines are in stock at the pharmacy.")
                            else:
                                st.warning("Some medicines may not be in stock. Alternatives have been suggested to the pharmacist.")

                        # Transition workflow
                        try:
                            transition_state(
                                appt["id"], appt["patient_id"],
                                "prescribed", profile["id"], "doctor",
                                f"Prescription {rx_result.get('prescription_code', '')} created",
                            )
                        except Exception:
                            pass
                    else:
                        st.error("Prescription rejected by AI validation. Please correct the errors below and resubmit.")
                        
                        # Show validation results as errors
                        validation = rx_result.get("validation", {})
                        if validation.get("warnings"):
                            for w in validation["warnings"]:
                                st.error(f"Dosage/Route Error: {w}")
                        if validation.get("interactions"):
                            for i in validation["interactions"]:
                                st.error(f"Drug Interaction: {i}")
                        if validation.get("allergy_alerts"):
                            for a in validation["allergy_alerts"]:
                                st.error(f"Allergy Alert: {a}")
                        if validation.get("suggestions"):
                            for s in validation["suggestions"]:
                                st.info(f"AI Suggestion: {s}")

                    if result.get("messages"):
                        with st.expander("AI Agent Log"):
                            for msg in result["messages"]:
                                st.text(msg)

                render_prescription_form(
                    consultation_id=consult["id"],
                    patient_id=appt["patient_id"],
                    doctor_id=doctor["id"],
                    on_submit=handle_prescription_submit,
                    consult_data=consult,
                )

    except Exception as e:
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 4: Patient History
# ══════════════════════════════════════════════════════════════
elif active_tab == "Patient History":
    st.markdown("### Patient History Lookup")

    col_s1, col_s2 = st.columns([4, 1])
    with col_s1:
        search = st.text_input("Search patient by ID or name", placeholder="MF-XXXXXXXX", label_visibility="collapsed")
    with col_s2:
        search_btn = st.button("Search", use_container_width=True)

    if search or search_btn:
        try:
            patients = db.search_patients(search)
            for p in patients:
                p_user = p.get("users", {}) or {}
                with st.expander(f"{p_user.get('full_name', 'Unknown')} — {p.get('patient_id_code', 'N/A')}"):
                    st.markdown(f"**Allergies:** {', '.join(p.get('allergies') or []) or 'None'}")
                    st.markdown(f"**Conditions:** {', '.join(p.get('chronic_conditions') or []) or 'None'}")

                    consults = db.get_consultations_by_patient(p["id"])
                    if consults:
                        st.markdown("##### Consultation History")
                        for c in consults[:5]:
                            doc_name = c.get('doctors', {}).get('users', {}).get('full_name', 'Unknown Doctor')
                            date_str = c.get('created_at', 'N/A')[:10]
                            with st.expander(f"{date_str} - Dr. {doc_name} ({c.get('diagnosis', 'No diagnosis')})"):
                                st.markdown(f"**Symptoms:** {c.get('symptoms', 'None recorded')}")
                                st.markdown(f"**Examination Notes:** {c.get('examination_notes', 'None recorded')}")
                                st.markdown(f"**Diagnosis:** {c.get('diagnosis', 'None recorded')}")
                                if c.get('additional_notes'):
                                    st.markdown(f"**Additional Notes:** {c.get('additional_notes')}")
                    else:
                        st.caption("No consultation history.")
        except Exception as e:
            st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 5: Settings
# ══════════════════════════════════════════════════════════════
elif active_tab == "Settings":
    st.markdown("### Doctor Settings")

    dept_info = doctor.get("departments", {}) or {}

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"**Department:** {dept_info.get('name', 'N/A')}")
        st.markdown(f"**Specialization:** {doctor.get('specialization', 'N/A')}")
        st.markdown(f"**Qualification:** {doctor.get('qualification', 'N/A')}")
        st.markdown(f"**Experience:** {doctor.get('experience_years', 0)} years")

    with col2:
        st.markdown(f"**Max Daily Patients:** {doctor.get('max_daily_patients', 30)}")
        st.markdown(f"**Consultation Fee:** ₹{doctor.get('consultation_fee', 0)}")
        st.markdown(f"**License:** {doctor.get('license_number', 'N/A')}")

    # Status toggle
    st.markdown("---")
    st.markdown("#### Availability Status")
    status_options = ["available", "busy", "on_break", "offline"]
    status_labels = {"available": "Available", "busy": "Busy", "on_break": "On Break", "offline": "Offline"}

    def update_status():
        new_status = st.session_state.doctor_status_select
        db.update_doctor_status(doctor["id"], new_status)
        st.toast(f"Status updated to {status_labels[new_status]}")

    st.selectbox(
        "Set Status",
        options=status_options,
        index=status_options.index(doctor.get("status", "offline")),
        format_func=lambda x: status_labels.get(x, x),
        key="doctor_status_select",
        on_change=update_status
    )
