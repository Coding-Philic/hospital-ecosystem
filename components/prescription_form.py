"""
MediFlow AI — Prescription Form Component
============================================
Structured medicine entry for doctors with autocomplete, dosage, and AI validation.
"""

import streamlit as st
from database import queries as db
from utils.constants import DOSAGE_FREQUENCIES, MEDICINE_ROUTES, DURATION_UNITS


def render_prescription_form(consultation_id: str, patient_id: str, doctor_id: str, on_submit=None, consult_data: dict = None):
    """
    Render the prescription entry form for doctors.

    Args:
        consultation_id: The consultation to attach the prescription to
        patient_id: The patient receiving the prescription
        doctor_id: The prescribing doctor
        on_submit: Callback with prescription items on submission
        consult_data: The consultation data for AI generation
    """
    st.markdown("#### Write Prescription")

    # Initialize prescription items in session state
    if "prescription_items" not in st.session_state:
        st.session_state.prescription_items = []

    # Medicine catalog for autocomplete
    try:
        medicines = db.get_all_medicines()
        medicine_names = [m["name"] for m in medicines]
    except Exception:
        medicine_names = []

    # Initialize widget keys directly
    if "rx_medicine_sel" not in st.session_state:
        st.session_state.rx_medicine_sel = "-- Select or type --" if medicine_names else ""
    if "rx_medicine_custom" not in st.session_state:
        st.session_state.rx_medicine_custom = ""
    if "rx_medicine_name_input" not in st.session_state:
        st.session_state.rx_medicine_name_input = ""
    if "rx_dosage_input" not in st.session_state:
        st.session_state.rx_dosage_input = ""
    if "rx_duration_val_input" not in st.session_state:
        st.session_state.rx_duration_val_input = 5
    if "rx_duration_unit_input" not in st.session_state:
        st.session_state.rx_duration_unit_input = "days"
    if "rx_quantity_input" not in st.session_state:
        st.session_state.rx_quantity_input = 10
    if "rx_instructions_input" not in st.session_state:
        st.session_state.rx_instructions_input = ""
    if "rx_route_input" not in st.session_state:
        st.session_state.rx_route_input = "Oral"
    if "rx_frequency_input" not in st.session_state:
        st.session_state.rx_frequency_input = "Once daily (OD)"

    if st.session_state.pop("rx_scroll_top", False):
        st.components.v1.html("<script>window.parent.document.querySelector('.main').scrollTo(0, 0);</script>", height=0)

    # Check if we are pulling an item for edit
    edit_item = st.session_state.pop("rx_edit_item", None)
    if edit_item:
        med_name = edit_item.get("medicine_name", "")
        # Populate widget states directly
        if medicine_names:
            st.session_state.rx_medicine_sel = med_name if med_name in medicine_names else "-- Select or type --"
        st.session_state.rx_medicine_custom = med_name
        st.session_state.rx_medicine_name_input = med_name
        
        st.session_state.rx_dosage_input = edit_item.get("dosage", "")
        st.session_state.rx_frequency_input = edit_item.get("frequency", "Once daily (OD)")
        st.session_state.rx_route_input = edit_item.get("route", "Oral")
        
        duration = edit_item.get("duration", "5 days").split(" ")
        if len(duration) == 2:
            try:
                st.session_state.rx_duration_val_input = int(duration[0])
            except:
                st.session_state.rx_duration_val_input = 5
            st.session_state.rx_duration_unit_input = duration[1]
            
        try:
            st.session_state.rx_quantity_input = int(edit_item.get("quantity", 10))
        except:
            st.session_state.rx_quantity_input = 10
            
        st.session_state.rx_instructions_input = edit_item.get("instructions", "")

    # Auto-Generate Prescription Button
    if consult_data:
        if st.button("✨ Auto-Generate Prescription", type="primary", use_container_width=True):
            with st.spinner("AI is generating prescription from consultation..."):
                from agents.prescription_agent import generate_prescription_from_consult
                generated_items = generate_prescription_from_consult(consult_data)
                if generated_items:
                    st.session_state.prescription_items.extend(generated_items)
                    st.success("Prescription generated successfully!")
                    st.rerun()

    # Add medicine item form
    with st.expander("Add Medicine", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            if medicine_names:
                medicine_name_sel = st.selectbox(
                    "Medicine Name",
                    options=["-- Select or type --"] + medicine_names,
                    key="rx_medicine_sel",
                )
                if medicine_name_sel == "-- Select or type --":
                    medicine_name = st.text_input("Or type medicine name", key="rx_medicine_custom")
                else:
                    medicine_name = medicine_name_sel
            else:
                medicine_name = st.text_input("Medicine Name", key="rx_medicine_name_input")

            dosage = st.text_input("Dosage", placeholder="e.g., 500mg, 10ml", key="rx_dosage_input")

        with col2:
            frequency = st.selectbox("Frequency", options=DOSAGE_FREQUENCIES, key="rx_frequency_input")
            route = st.selectbox("Route", options=MEDICINE_ROUTES, key="rx_route_input")

        col3, col4 = st.columns(2)
        with col3:
            duration_val = st.number_input("Duration", min_value=1, key="rx_duration_val_input")
            duration_unit = st.selectbox("Unit", options=DURATION_UNITS, key="rx_duration_unit_input")
        with col4:
            quantity = st.number_input("Quantity (tablets/units)", min_value=1, key="rx_quantity_input")
            instructions = st.text_input("Special Instructions", placeholder="e.g., Take after meals", key="rx_instructions_input")

        edit_idx = st.session_state.get("rx_edit_index")
        btn_label = "Update Prescription Item" if edit_idx is not None else "Add to Prescription"

        if st.button(btn_label, use_container_width=True):
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
                
                if edit_idx is not None:
                    st.session_state.prescription_items[edit_idx] = item
                    st.session_state.pop("rx_edit_index", None)
                    st.success(f"Updated: {medicine_name} {dosage}")
                else:
                    st.session_state.prescription_items.append(item)
                    st.success(f"Added: {medicine_name} {dosage}")
                
                # Clear state
                st.session_state.rx_medicine_sel = "-- Select or type --" if medicine_names else ""
                st.session_state.rx_medicine_custom = ""
                st.session_state.rx_medicine_name_input = ""
                st.session_state.rx_dosage_input = ""
                st.session_state.rx_duration_val_input = 5
                st.session_state.rx_duration_unit_input = "days"
                st.session_state.rx_quantity_input = 10
                st.session_state.rx_instructions_input = ""
                st.session_state.rx_route_input = "Oral"
                st.session_state.rx_frequency_input = "Once daily (OD)"
                
                st.rerun()
            else:
                st.warning("Please fill in medicine name and dosage.")

    # Display current items
    if st.session_state.prescription_items:
        st.markdown("#### Current Prescription Items")

        for idx, item in enumerate(st.session_state.prescription_items):
            # Highlight item if it's currently being edited
            is_editing = st.session_state.get("rx_edit_index") == idx
            
            if is_editing:
                st.markdown(f"<div style='border-left: 3px solid #3b82f6; padding-left: 10px; background-color: #3b82f615;'>", unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns([3, 3, 1, 1])
            with col1:
                st.markdown(f"**{idx+1}. {item['medicine_name']}** — {item['dosage']}")
            with col2:
                st.markdown(f"{item['frequency']} | {item['duration']} | {item['route']}")
            with col3:
                if st.button("Editing..." if is_editing else "Edit", key=f"edit_rx_{idx}", disabled=is_editing):
                    st.session_state.rx_edit_index = idx
                    st.session_state.rx_edit_item = item
                    st.session_state.rx_scroll_top = True
                    st.rerun()
            with col4:
                if st.button("Remove", key=f"remove_rx_{idx}"):
                    st.session_state.prescription_items.pop(idx)
                    # Adjust edit_index if we removed an item above it
                    if edit_idx is not None:
                        if edit_idx == idx:
                            st.session_state.pop("rx_edit_index", None)
                        elif edit_idx > idx:
                            st.session_state.rx_edit_index = edit_idx - 1
                    st.rerun()

            if item.get("instructions"):
                st.caption(f"   Note: {item['instructions']}")
                
            if is_editing:
                st.markdown("</div>", unsafe_allow_html=True)
                
            st.markdown("---")

        # Submit prescription
        col_submit, col_clear = st.columns(2)
        with col_submit:
            if st.button("Submit Prescription", use_container_width=True, type="primary"):
                if on_submit:
                    on_submit(st.session_state.prescription_items)
        with col_clear:
            if st.button("Clear All", use_container_width=True):
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
        background: var(--card-bg);
        border: 1px solid var(--border-color);
        border-left: 3px solid {status_color};
        border-radius: 6px;
        padding: 1.2rem;
        margin-bottom: 1rem;
    ">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.8rem;">
            <div>
                <span style="color: var(--text-secondary); font-size: 0.8rem;">Prescription</span><br/>
                <span style="color: var(--text-primary); font-weight: 700; font-size: 1.1rem;">
                    {prescription.get('prescription_code', 'N/A')}
                </span>
            </div>
            <div style="
                background: {status_color}18;
                color: {status_color};
                padding: 4px 14px;
                border-radius: 4px;
                font-weight: 600;
                font-size: 0.8rem;
            ">
                {status.replace('_', ' ').title()}
            </div>
        </div>
        <div style="color: var(--text-secondary); font-size: 0.85rem; margin-bottom: 0.5rem;">
            Prescribed by: Dr. {doc_user.get('full_name', 'Unknown')}
        </div>
    </div>
    """, unsafe_allow_html=True)

    if items:
        for item in items:
            in_stock = item.get("is_in_stock")
            stock_label = "In Stock" if in_stock else ("Out of Stock" if in_stock is False else "Unknown")

            st.markdown(f"""
            **{item.get('medicine_name', 'N/A')}** — {item.get('dosage', '')}
            - Frequency: {item.get('frequency', '')} | Duration: {item.get('duration', '')}
            - Route: {item.get('route', 'Oral')} | Qty: {item.get('quantity', 1)} | Stock: {stock_label}
            """)
            if item.get("instructions"):
                st.caption(f"   Note: {item['instructions']}")
