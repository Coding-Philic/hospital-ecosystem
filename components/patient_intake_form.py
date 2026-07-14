"""
MediFlow AI — Patient Intake Form Component
=============================================
Multi-step digital intake form for new and returning patients.
"""

import streamlit as st
from datetime import date, datetime
from database import queries as db
from database.supabase_client import get_current_user
from utils.helpers import generate_patient_id, calculate_age
from utils.constants import BLOOD_GROUPS, GENDER_OPTIONS, INSURANCE_PROVIDERS


def render_intake_form(on_submit=None):
    """
    Render the digital patient intake form.

    Args:
        on_submit: Callback function called with patient data on form submission
    """
    profile = get_current_user()
    if not profile:
        st.error("Please log in first.")
        return

    # Check if patient record already exists
    existing_patient = db.get_patient_by_user_id(profile["id"])

    if existing_patient:
        st.success("✅ Your intake form is already on file. You can update it below.")
        _render_update_form(existing_patient, profile)
    else:
        st.info("📋 Please fill out this intake form. It's saved permanently and reused on every visit.")
        _render_new_form(profile, on_submit)


def _render_new_form(profile: dict, on_submit=None):
    """Render the intake form for new patients."""
    with st.form("intake_form", clear_on_submit=False):
        st.markdown("#### Personal Information")

        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name", value=profile.get("full_name", ""), disabled=True)
            dob = st.date_input("Date of Birth", value=date(2000, 1, 1), min_value=date(1920, 1, 1), max_value=date.today())
            gender = st.selectbox("Gender", options=GENDER_OPTIONS)

        with col2:
            email = st.text_input("Email", value=profile.get("email", ""), disabled=True)
            phone = st.text_input("Phone", value=profile.get("phone", ""))
            blood_group = st.selectbox("Blood Group", options=BLOOD_GROUPS)

        address = st.text_area("Address", placeholder="Full address", height=80)

        st.markdown("---")
        st.markdown("#### Emergency Contact")
        col3, col4 = st.columns(2)
        with col3:
            emergency_name = st.text_input("Emergency Contact Name")
        with col4:
            emergency_phone = st.text_input("Emergency Contact Phone")

        st.markdown("---")
        st.markdown("#### Medical History")

        allergies_text = st.text_input(
            "Known Allergies",
            placeholder="e.g., Penicillin, Peanuts (comma-separated)",
        )
        conditions_text = st.text_input(
            "Chronic Conditions",
            placeholder="e.g., Diabetes, Hypertension (comma-separated)",
        )

        st.markdown("---")
        st.markdown("#### Insurance Information")
        col5, col6 = st.columns(2)
        with col5:
            insurance_provider = st.selectbox("Insurance Provider", options=INSURANCE_PROVIDERS)
        with col6:
            insurance_id = st.text_input("Insurance ID / Policy Number", placeholder="Optional")

        submitted = st.form_submit_button("💾 Save Intake Form", use_container_width=True, type="primary")

        if submitted:
            # Parse lists
            allergies = [a.strip() for a in allergies_text.split(",") if a.strip()] if allergies_text else []
            conditions = [c.strip() for c in conditions_text.split(",") if c.strip()] if conditions_text else []

            patient_code = generate_patient_id()

            patient_data = {
                "user_id": profile["id"],
                "patient_id_code": patient_code,
                "date_of_birth": dob.isoformat(),
                "gender": gender,
                "blood_group": blood_group,
                "address": address,
                "emergency_contact_name": emergency_name,
                "emergency_contact_phone": emergency_phone,
                "insurance_provider": insurance_provider,
                "insurance_id": insurance_id,
                "allergies": allergies,
                "chronic_conditions": conditions,
            }

            try:
                result = db.create_patient(patient_data)
                if result:
                    st.success(f"✅ Intake form saved! Your Patient ID: **{patient_code}**")
                    st.balloons()
                    if on_submit:
                        on_submit(result[0] if isinstance(result, list) else result)
                    st.rerun()
                else:
                    st.error("Failed to save intake form.")
            except Exception as e:
                st.error(f"Error: {str(e)}")


def _render_update_form(patient: dict, profile: dict):
    """Render an editable form for existing patients."""
    user_info = patient.get("users", {}) or {}

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1e293b, #334155);
        padding: 1rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        border-left: 4px solid #6366f1;
    ">
        <strong>Patient ID:</strong> {patient.get('patient_id_code', 'N/A')}<br/>
        <strong>Name:</strong> {user_info.get('full_name', profile.get('full_name', 'N/A'))}<br/>
        <strong>Blood Group:</strong> {patient.get('blood_group', 'Unknown')}<br/>
        <strong>Allergies:</strong> {', '.join(patient.get('allergies') or []) or 'None'}<br/>
        <strong>Conditions:</strong> {', '.join(patient.get('chronic_conditions') or []) or 'None'}<br/>
        <strong>Insurance:</strong> {patient.get('insurance_provider', 'None')}
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📝 Update Information"):
        with st.form("update_intake_form"):
            allergies_text = st.text_input(
                "Allergies",
                value=", ".join(patient.get("allergies") or []),
            )
            conditions_text = st.text_input(
                "Chronic Conditions",
                value=", ".join(patient.get("chronic_conditions") or []),
            )
            address = st.text_area("Address", value=patient.get("address", ""))
            emergency_name = st.text_input("Emergency Contact", value=patient.get("emergency_contact_name", ""))
            emergency_phone = st.text_input("Emergency Phone", value=patient.get("emergency_contact_phone", ""))

            if st.form_submit_button("💾 Update", use_container_width=True):
                allergies = [a.strip() for a in allergies_text.split(",") if a.strip()]
                conditions = [c.strip() for c in conditions_text.split(",") if c.strip()]
                db.update_patient(patient["id"], {
                    "allergies": allergies,
                    "chronic_conditions": conditions,
                    "address": address,
                    "emergency_contact_name": emergency_name,
                    "emergency_contact_phone": emergency_phone,
                })
                st.success("✅ Information updated!")
                st.rerun()
