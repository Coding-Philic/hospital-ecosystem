"""
MediFlow AI — Prescription Form Component
============================================
Structured medicine entry for doctors with autocomplete, dosage, and AI validation.
"""

import streamlit as st
from database import queries as db
from utils.constants import DOSAGE_FREQUENCIES, MEDICINE_ROUTES, DURATION_UNITS


def render_prescription_form(consultation_id: str, patient_id: str, doctor_id: str, on_submit=None):
    """
    Render the prescription entry form for doctors.

    Args:
        consultation_id: The consultation to attach the prescription to
        patient_id: The patient receiving the prescription
        doctor_id: The prescribing doctor
        on_submit: Callback with prescription items on submission
    """
    st.markdown("#### 📝 Write Prescription")

    # Initialize prescription items in session state
    if "prescription_items" not in st.session_state:
        st.session_state.prescription_items = []

    # Medicine catalog for autocomplete
    try:
        medicines = db.get_all_medicines()
        medicine_names = [m["name"] for m in medicines]
    except Exception:
        medicine_names = []

    # Add medicine item form
    with st.expander("➕ Add Medicine", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            if medicine_names:
                medicine_name = st.selectbox(
                    "Medicine Name",
                    options=["-- Select or type --"] + medicine_names,
                    key="rx_medicine",
                )
                if medicine_name == "-- Select or type --":
                    medicine_name = st.text_input("Or type medicine name", key="rx_medicine_custom")
            else:
                medicine_name = st.text_input("Medicine Name", key="rx_medicine_name")

            dosage = st.text_input("Dosage", placeholder="e.g., 500mg, 10ml", key="rx_dosage")

        with col2:
            frequency = st.selectbox("Frequency", options=DOSAGE_FREQUENCIES, key="rx_frequency")
            route = st.selectbox("Route", options=MEDICINE_ROUTES, key="rx_route")

        col3, col4 = st.columns(2)
        with col3:
            duration_val = st.number_input("Duration", min_value=1, value=5, key="rx_duration_val")
            duration_unit = st.selectbox("Unit", options=DURATION_UNITS, key="rx_duration_unit")
        with col4:
            quantity = st.number_input("Quantity (tablets/units)", min_value=1, value=10, key="rx_quantity")
            instructions = st.text_input("Special Instructions", placeholder="e.g., Take after meals", key="rx_instructions")

        if st.button("➕ Add to Prescription", use_container_width=True):
            if medicine_name and medicine_name != "-- Select or type --" and dosage:
                item = {
                    "medicine_name": medicine_name,
                    "dosage": dosage,
                    "frequency": frequency,
                    "duration": f"{duration_val} {duration_unit}",
                    "route": route,
                    "quantity": quantity,
                    "instructions": instructions,
                }
                st.session_state.prescription_items.append(item)
                st.success(f"✅ Added: {medicine_name} {dosage}")
                st.rerun()
            else:
                st.warning("Please fill in medicine name and dosage.")

    # Display current items
    if st.session_state.prescription_items:
        st.markdown("#### 📋 Current Prescription Items")

        for idx, item in enumerate(st.session_state.prescription_items):
            col1, col2, col3 = st.columns([4, 4, 1])
            with col1:
                st.markdown(f"""
                **{idx+1}. {item['medicine_name']}** — {item['dosage']}
                """)
            with col2:
                st.markdown(f"""
                {item['frequency']} | {item['duration']} | {item['route']}
                """)
            with col3:
                if st.button("🗑️", key=f"remove_rx_{idx}"):
                    st.session_state.prescription_items.pop(idx)
                    st.rerun()

            if item.get("instructions"):
                st.caption(f"   📌 {item['instructions']}")
            st.markdown("---")

        # Submit prescription
        col_submit, col_clear = st.columns(2)
        with col_submit:
            if st.button("✅ Submit Prescription", use_container_width=True, type="primary"):
                if on_submit:
                    on_submit(st.session_state.prescription_items)
                st.session_state.prescription_items = []
        with col_clear:
            if st.button("🗑️ Clear All", use_container_width=True):
                st.session_state.prescription_items = []
                st.rerun()
    else:
        st.info("No items added yet. Use the form above to add medicines.")


def render_prescription_view(prescription: dict):
    """
    Render a read-only view of a prescription (for patients and pharmacy).
    """
    items = prescription.get("prescription_items", [])
    doctor_info = prescription.get("doctors", {}) or {}
    doc_user = doctor_info.get("users", {}) or {}

    status_colors = {
        "created": "#f59e0b",
        "sent_to_pharmacy": "#3b82f6",
        "partially_available": "#f97316",
        "dispensed": "#22c55e",
        "cancelled": "#ef4444",
    }
    status = prescription.get("status", "created")
    status_color = status_colors.get(status, "#94a3b8")

    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #1e293b, #0f172a);
        border: 1px solid #475569;
        border-radius: 12px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
            <div>
                <span style="color: #94a3b8; font-size: 0.8rem;">Prescription</span><br/>
                <span style="color: white; font-weight: 700; font-size: 1.1rem;">
                    {prescription.get('prescription_code', 'N/A')}
                </span>
            </div>
            <div style="
                background: {status_color}20;
                color: {status_color};
                padding: 4px 14px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 0.85rem;
            ">
                {status.replace('_', ' ').title()}
            </div>
        </div>
        <div style="color: #94a3b8; font-size: 0.85rem; margin-bottom: 0.5rem;">
            Prescribed by: Dr. {doc_user.get('full_name', 'Unknown')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if items:
        for item in items:
            in_stock = item.get("is_in_stock")
            stock_icon = "✅" if in_stock else ("❌" if in_stock is False else "❓")

            st.markdown(f"""
            💊 **{item.get('medicine_name', 'N/A')}** — {item.get('dosage', '')}
            - Frequency: {item.get('frequency', '')} | Duration: {item.get('duration', '')}
            - Route: {item.get('route', 'Oral')} | Qty: {item.get('quantity', 1)} | Stock: {stock_icon}
            """)
            if item.get("instructions"):
                st.caption(f"   📌 {item['instructions']}")
