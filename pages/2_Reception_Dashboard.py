"""
MediFlow AI — Reception Dashboard
==========================================
Receptionist dashboard for:
- Live patient queue overview
- New patient registration
- AI triage confirmation/override
- Patient search
- Workflow state management
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.auth import require_auth
from components.navbar import render_navbar
from components.queue_display import render_department_queue, render_metric_card
from components.workflow_tracker import render_mini_status, render_workflow_tracker
from database.supabase_client import get_current_user
from database import queries as db
from agents.workflow_agent import transition_state, get_valid_next_states, get_current_state
from config import config

st.set_page_config(page_title="Reception — MediFlow AI", layout="wide")

require_auth(allowed_roles=["receptionist", "admin"])
render_navbar()

profile = get_current_user()

st.markdown("# Reception Dashboard")

# ── Active Tab Logic ────────────────────────────────────────────
active_tab = st.session_state.get("active_tab", "Live Queue")

# ══════════════════════════════════════════════════════════════
# TAB 1: Live Queue
# ══════════════════════════════════════════════════════════════
if active_tab == "Live Queue":
    st.markdown("### Today's Patient Queue")

    # Stats row
    try:
        stats = db.get_today_stats()
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            render_metric_card("Waiting", stats.get("waiting_patients", 0), color="#007B8A")
        with col2:
            render_metric_card("In Progress", stats.get("in_progress", 0), color="#3A9AD9")
        with col3:
            render_metric_card("Completed", stats.get("completed_consultations", 0), color="#005F6B")
        with col4:
            render_metric_card("Total Today", stats.get("total_appointments", 0), color="#6BCBEB")
    except Exception:
        pass

    st.markdown("---")

    # Department filter
    departments = db.get_all_departments()
    dept_names = ["All Departments"] + [d["name"] for d in departments]
    selected_dept = st.selectbox("Filter by Department", dept_names, key="queue_dept_filter")

    dept_id = None
    if selected_dept != "All Departments":
        for d in departments:
            if d["name"] == selected_dept:
                dept_id = d["id"]
                break

    # Fetch and display queue
    try:
        appointments = db.get_today_appointments(dept_id)
        render_department_queue(appointments, selected_dept)
    except Exception as e:
        st.error(f"Error loading queue: {e}")

    # Auto-refresh
    if st.button("Refresh Queue"):
        st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB 2: Triage Confirmation (AI Override)
# ══════════════════════════════════════════════════════════════
elif active_tab == "Triage Confirmation":
    st.markdown("### AI Triage Confirmation")
    st.info("Review AI-recommended department and urgency assignments. Confirm or override before finalizing.")

    try:
        departments = db.get_all_departments()
        if not departments:
            departments = [{"id": "0", "name": "General"}] # Fallback
            
        # Get appointments pending confirmation
        today_appts = db.get_today_appointments()
        unconfirmed = [a for a in today_appts if not a.get("receptionist_confirmed")]

        if not unconfirmed:
            st.success("All triage assignments have been confirmed.")
        else:
            for appt in unconfirmed:
                patient_info = appt.get("patients", {}) or {}
                user_info = patient_info.get("users", {}) or {}
                dept_info = appt.get("departments", {}) or {}

                with st.expander(
                    f"{appt.get('token_number', 'N/A')} — {user_info.get('full_name', 'Unknown')} "
                    f"| AI: {appt.get('ai_recommended_department', 'N/A')} "
                    f"({appt.get('ai_urgency_score', 'N/A')})",
                    expanded=True,
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Patient:** {user_info.get('full_name', 'Unknown')}")
                        st.markdown(f"**Symptoms:** {appt.get('symptom_summary', 'N/A')}")
                        st.markdown(f"**AI Department:** {appt.get('ai_recommended_department', 'N/A')}")
                        st.markdown(f"**AI Urgency:** {appt.get('ai_urgency_score', 'N/A')}")
                        confidence = appt.get("ai_confidence", 0)
                        st.markdown(f"**AI Confidence:** {float(confidence):.0%}" if confidence else "")

                    with col2:
                        # Override options
                        override_dept = st.selectbox(
                            "Confirm/Override Department",
                            options=[d["name"] for d in departments],
                            index=[d["name"] for d in departments].index(
                                appt.get("ai_recommended_department", departments[0]["name"])
                            ) if appt.get("ai_recommended_department") in [d["name"] for d in departments] else 0,
                            key=f"dept_override_{appt['id']}",
                        )

                        urgency_options = list(config.URGENCY_LEVELS.keys())
                        override_urgency = st.selectbox(
                            "Confirm/Override Urgency",
                            options=urgency_options,
                            index=urgency_options.index(appt.get("urgency", "routine")),
                            format_func=lambda x: config.URGENCY_LEVELS[x]["label"],
                            key=f"urgency_override_{appt['id']}",
                        )

                        col_confirm, col_skip = st.columns(2)
                        with col_confirm:
                            if st.button("Confirm", key=f"confirm_{appt['id']}", use_container_width=True, type="primary"):
                                update_data = {
                                    "receptionist_confirmed": True,
                                    "confirmed_by": profile["id"],
                                    "urgency": override_urgency,
                                }

                                # If department overridden, update
                                if override_dept != appt.get("ai_recommended_department"):
                                    for d in departments:
                                        if d["name"] == override_dept:
                                            update_data["department_id"] = d["id"]
                                            break

                                    # Log override
                                    db.create_audit_entry({
                                        "actor_id": profile["id"],
                                        "actor_role": "receptionist",
                                        "action": "override_department",
                                        "entity_type": "appointment",
                                        "entity_id": appt["id"],
                                        "details": {
                                            "ai_recommended": appt.get("ai_recommended_department"),
                                            "overridden_to": override_dept,
                                        },
                                        "was_overridden": True,
                                    })

                                db.update_appointment(appt["id"], update_data)

                                # Transition workflow
                                try:
                                    patient_data = appt.get("patients", {})
                                    if patient_data:
                                        transition_state(
                                            appointment_id=appt["id"],
                                            patient_id=appt["patient_id"],
                                            new_state="queued",
                                            transitioned_by=profile["id"],
                                            transitioned_by_role="receptionist",
                                            notes=f"Confirmed by reception. Department: {override_dept}",
                                        )
                                except Exception:
                                    pass

                                st.success("Confirmed.")
                                st.rerun()

    except Exception as e:
        st.error(f"Error loading triage data: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 3: Register Patient
# ══════════════════════════════════════════════════════════════
elif active_tab == "Register Patient":
    st.markdown("### New Patient Registration")
    st.info("Register a walk-in patient who doesn't have an account.")

    from database.supabase_client import sign_up
    from utils.helpers import generate_patient_id

    with st.form("register_patient_form"):
        st.markdown("#### Patient Information")
        col1, col2 = st.columns(2)
        with col1:
            reg_name = st.text_input("Full Name", key="reg_name")
            reg_email = st.text_input("Email", key="reg_email")
            reg_phone = st.text_input("Phone", key="reg_phone")
        with col2:
            from utils.constants import GENDER_OPTIONS, BLOOD_GROUPS
            reg_gender = st.selectbox("Gender", GENDER_OPTIONS, key="reg_gender")
            reg_blood = st.selectbox("Blood Group", BLOOD_GROUPS, key="reg_blood")
            reg_dob = st.date_input("Date of Birth", key="reg_dob")

        reg_allergies = st.text_input("Known Allergies (comma-separated)", key="reg_allergies")
        reg_conditions = st.text_input("Chronic Conditions (comma-separated)", key="reg_conditions")

        if st.form_submit_button("Register Patient", use_container_width=True, type="primary"):
            if not reg_name or not reg_email:
                st.error("Name and email are required.")
            else:
                with st.spinner("Registering..."):
                    # Create user account
                    import random, string
                    temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    result = sign_up(reg_email, temp_password, reg_name, "patient", reg_phone)

                    if result["success"]:
                        # Create patient record
                        patient_code = generate_patient_id()
                        allergies = [a.strip() for a in reg_allergies.split(",") if a.strip()] if reg_allergies else []
                        conditions = [c.strip() for c in reg_conditions.split(",") if c.strip()] if reg_conditions else []

                        try:
                            db.create_patient({
                                "user_id": str(result["user"].id),
                                "patient_id_code": patient_code,
                                "date_of_birth": reg_dob.isoformat(),
                                "gender": reg_gender,
                                "blood_group": reg_blood,
                                "allergies": allergies,
                                "chronic_conditions": conditions,
                            })
                            st.success(f"Patient registered. ID: **{patient_code}** | Temp password: **{temp_password}**")
                        except Exception as e:
                            st.error(f"Error creating patient record: {e}")
                    else:
                        st.error(result["message"])


# ══════════════════════════════════════════════════════════════
# TAB 4: Search Patients
# ══════════════════════════════════════════════════════════════
elif active_tab == "Search":
    st.markdown("### Search Patients")

    search_term = st.text_input("Search by Patient ID or Name", placeholder="MF-XXXXXXXX or patient name")

    if search_term:
        try:
            results = db.search_patients(search_term)
            if results:
                for p in results:
                    user_info = p.get("users", {}) or {}
                    st.markdown(f"""
                    **{user_info.get('full_name', 'Unknown')}** — `{p.get('patient_id_code', 'N/A')}`
                    | Phone: {user_info.get('phone', 'N/A')}
                    | Blood: {p.get('blood_group', 'N/A')}
                    | Allergies: {', '.join(p.get('allergies') or []) or 'None'}
                    """)
                    st.markdown("---")
            else:
                st.info("No patients found.")
        except Exception as e:
            st.error(f"Search error: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 5: Workflow Status View
# ══════════════════════════════════════════════════════════════
elif active_tab == "Workflow Overview":
    st.markdown("### Workflow State Overview")
    st.info("See where every patient currently is in their journey.")

    from utils.constants import WORKFLOW_DISPLAY

    try:
        today_appts = db.get_today_appointments()
        if today_appts:
            # Group by workflow state
            for state_key, display in WORKFLOW_DISPLAY.items():
                state_patients = []
                for appt in today_appts:
                    try:
                        current = get_current_state(appt["id"])
                        if current == state_key:
                            state_patients.append(appt)
                    except Exception:
                        pass

                if state_patients:
                    st.markdown(f"#### {display['label']} ({len(state_patients)})")
                    for appt in state_patients:
                        p_info = appt.get("patients", {}) or {}
                        p_user = p_info.get("users", {}) or {}
                        
                        with st.container(border=True):
                            st.markdown(f"##### {appt.get('token_number', 'N/A')} — {p_user.get('full_name', 'Unknown')}")
                            # Render the full visual progress bar for the patient's journey
                            render_workflow_tracker(state_key)
                    st.markdown("---")
        else:
            st.info("No appointments today.")
    except Exception as e:
        st.error(f"Error: {e}")

# ══════════════════════════════════════════════════════════════
# TAB 6: Billing & Discharge
# ══════════════════════════════════════════════════════════════
elif active_tab == "Billing & Discharge":
    st.markdown("### Billing & Discharge")
    st.info("Calculate final bills and discharge active patients.")

    try:
        active_appts = db.get_active_appointments_for_billing()
        if not active_appts:
            st.success("No active patients waiting for billing/discharge.")
        else:
            # Let receptionist select a patient
            appt_options = {}
            for appt in active_appts:
                p_info = appt.get("patients", {}) or {}
                p_user = p_info.get("users", {}) or {}
                token = appt.get("token_number", "N/A")
                name = p_user.get("full_name", "Unknown")
                appt_options[f"{token} — {name}"] = appt

            selected_str = st.selectbox("Select Patient to Bill/Discharge", options=list(appt_options.keys()))
            if selected_str:
                selected_appt = appt_options[selected_str]
                st.markdown("---")
                
                # Fetch billing details
                with st.spinner("Calculating bill..."):
                    bill_data = db.get_billing_details(selected_appt["id"])
                    
                doc_info = selected_appt.get("doctors", {}) or {}
                doc_fee = doc_info.get("consultation_fee") or 0.0
                
                pharmacy_total = 0.0
                rx_items = []
                for rx in bill_data.get("prescriptions", []):
                    for item in rx.get("prescription_items", []):
                        med = item.get("medicine", {}) or {}
                        qty = item.get("quantity", 0)
                        price = med.get("unit_price") or 0.0
                        cost = float(qty) * float(price)
                        pharmacy_total += cost
                        rx_items.append({
                            "name": med.get("name", "Unknown Medicine"),
                            "qty": qty,
                            "price": price,
                            "total": cost
                        })

                grand_total = float(doc_fee) + pharmacy_total
                
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Invoice Details")
                    
                    st.markdown(f"**Consultation Fee (Dr. {doc_info.get('users', {}).get('full_name', '')}):** ₹{doc_fee:.2f}")
                    st.markdown("**Pharmacy Charges:**")
                    if not rx_items:
                        st.markdown("- *No medicines prescribed*")
                    else:
                        for item in rx_items:
                            st.markdown(f"- {item['name']} (x{item['qty']}) @ ₹{item['price']:.2f} = **₹{item['total']:.2f}**")
                    
                    st.markdown("---")
                    st.markdown(f"### Total Amount Due: ₹{grand_total:.2f}")
                
                with col2:
                    st.markdown("#### Actions")
                    st.info("Review the final bill with the patient. Once payment is settled, click the button below to discharge them.")
                    
                    if st.button("Settle Bill & Discharge", type="primary", use_container_width=True):
                        # Construct JSON invoice
                        invoice_data = {
                            "consultation_fee": float(doc_fee),
                            "pharmacy_items": rx_items,
                            "pharmacy_total": pharmacy_total,
                            "grand_total": grand_total
                        }
                        
                        try:
                            # 1. Ensure state is moved to billing (skip if already there)
                            current_state = get_current_state(selected_appt["id"])
                            if current_state != "billing":
                                transition_state(
                                    selected_appt["id"],
                                    selected_appt["patient_id"],
                                    "billing",
                                    profile["id"], "receptionist",
                                    "Moved to billing"
                                )
                                
                            # 2. Transition to discharged with invoice data in metadata
                            client = db.get_supabase_admin_client()
                            client.table("workflow_states").insert({
                                "appointment_id": selected_appt["id"],
                                "patient_id": selected_appt["patient_id"],
                                "current_state": "discharged",
                                "previous_state": "billing",
                                "transitioned_by_role": "receptionist",
                                "notes": "Patient discharged after bill settlement.",
                                "metadata": {"invoice": invoice_data}
                            }).execute()
                            
                            # 3. Update appointment status
                            client.table("appointments").update({
                                "status": "completed"
                            }).eq("id", selected_appt["id"]).execute()
                            
                            st.success(f"Bill settled (₹{grand_total:.2f}). Patient discharged!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Failed to discharge patient: {e}")

    except Exception as e:
        st.error(f"Error loading billing data: {e}")
