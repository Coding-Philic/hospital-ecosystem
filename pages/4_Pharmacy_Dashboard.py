"""
MediFlow AI — Pharmacy Dashboard
======================================
Pharmacist dashboard for:
- Incoming prescription queue
- Inventory management
- AI-suggested alternative review
- Dispense confirmation
- Stock alerts
"""

import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.auth import require_auth
from components.navbar import render_navbar
from components.prescription_form import render_prescription_view
from components.queue_display import render_metric_card
from database.supabase_client import get_current_user
from database import queries as db
from agents.pharmacy_agent import check_prescription_stock, dispense_prescription, approve_substitute
from agents.workflow_agent import transition_state

st.set_page_config(page_title="Pharmacy — MediFlow AI", layout="wide")

require_auth(allowed_roles=["pharmacist", "admin"])
render_navbar()

profile = get_current_user()

st.markdown("# Pharmacy Dashboard")

# ── Active Tab Logic ────────────────────────────────────────────
active_tab = st.session_state.get("active_tab", "Prescription Queue")

# ══════════════════════════════════════════════════════════════
# TAB 1: Prescription Queue
# ══════════════════════════════════════════════════════════════
if active_tab == "Prescription Queue":
    st.markdown("### Incoming Prescriptions")

    try:
        pending = db.get_pending_prescriptions()

        if not pending:
            st.success("No pending prescriptions. All caught up.")
        else:
            st.info(f"{len(pending)} prescription(s) pending processing")

            for rx in pending:
                patient_info = rx.get("patients", {}) or {}
                p_user = patient_info.get("users", {}) or {}
                doctor_info = rx.get("doctors", {}) or {}
                d_user = doctor_info.get("users", {}) or {}
                items = rx.get("prescription_items", [])

                with st.expander(
                    f"Rx: {rx.get('prescription_code', 'N/A')} — "
                    f"{p_user.get('full_name', 'Unknown')} | "
                    f"{len(items)} items | "
                    f"Status: {rx.get('status', 'N/A').replace('_', ' ').title()}",
                    expanded=True,
                ):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Patient:** {p_user.get('full_name', 'Unknown')}")
                        st.markdown(f"**Patient ID:** {patient_info.get('patient_id_code', 'N/A')}")
                        st.markdown(f"**Phone:** {p_user.get('phone', 'N/A')}")
                    with col2:
                        st.markdown(f"**Prescriber:** Dr. {d_user.get('full_name', 'Unknown')}")
                        st.markdown(f"**Date:** {rx.get('created_at', 'N/A')[:10]}")

                    st.markdown("---")
                    st.markdown("**Prescribed Items:**")

                    for item in items:
                        in_stock = item.get("is_in_stock")
                        stock_icon = "[In Stock]" if in_stock else ("[Out of Stock]" if in_stock is False else "[Unchecked]")

                        st.markdown(f"""
                        **{item.get('medicine_name', 'N/A')}** {stock_icon} — {item.get('dosage', '')}
                        | {item.get('frequency', '')} | {item.get('duration', '')} | Qty: {item.get('quantity', 1)}
                        """)
                        if item.get("instructions"):
                            st.caption(f"   Note: {item['instructions']}")

                    st.markdown("---")

                    # Action buttons
                    col_check, col_dispense = st.columns(2)

                    with col_check:
                        if st.button("Check Stock", key=f"check_{rx['id']}", use_container_width=True):
                            with st.spinner("Checking inventory..."):
                                result = check_prescription_stock(rx["id"])

                            if result.get("success"):
                                if result.get("all_in_stock"):
                                    st.success("All items in stock.")
                                else:
                                    st.warning("Some items need alternatives. Check Substitution Review tab.")

                                for item_result in result.get("items", []):
                                    icon = "[OK]" if item_result["status"] == "in_stock" else "[LOW/OUT]"
                                    st.markdown(f"{icon} {item_result['medicine_name']} — "
                                              f"Available: {item_result['quantity_available']} | "
                                              f"Required: {item_result['quantity_required']}")

                                st.rerun()
                            else:
                                st.error(result.get("message", "Stock check failed."))

                    with col_dispense:
                        if st.button("Dispense", key=f"dispense_{rx['id']}", use_container_width=True, type="primary"):
                            result = dispense_prescription(rx["id"], profile["id"])
                            if result["success"]:
                                st.success("Prescription dispensed.")
                                # Workflow transition
                                try:
                                    transition_state(
                                        rx.get("consultation_id", ""),
                                        rx["patient_id"],
                                        "dispensed",
                                        profile["id"], "pharmacist",
                                        f"Prescription {rx['prescription_code']} dispensed",
                                    )
                                except Exception:
                                    pass
                                st.rerun()
                            else:
                                st.error(result["message"])

    except Exception as e:
        st.error(f"Error loading prescriptions: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 2: Inventory Management
# ══════════════════════════════════════════════════════════════
elif active_tab == "Inventory":
    st.markdown("### Pharmacy Inventory")

    # Stats
    try:
        low_stock = db.get_low_stock_items()
        col1, col2 = st.columns(2)
        with col1:
            render_metric_card("Low Stock Items", len(low_stock), color="#ef4444")
        with col2:
            all_inventory = db.get_pharmacy_inventory()
            render_metric_card("Total Products", len(all_inventory), color="#007B8A")
    except Exception:
        all_inventory = []
        low_stock = []

    st.markdown("---")

    # Search
    search = st.text_input("Search Inventory", placeholder="Medicine name...", key="inv_search")

    # Display inventory
    try:
        if not all_inventory:
            all_inventory = db.get_pharmacy_inventory()

        for inv in all_inventory:
            med = inv.get("medicines", {}) or {}
            med_name = med.get("name", "Unknown")

            if search and search.lower() not in med_name.lower():
                continue

            qty = inv.get("quantity_available", 0)
            reorder = inv.get("reorder_level", 10)
            is_low = qty <= reorder

            color = "#ef4444" if qty == 0 else ("#f59e0b" if is_low else "#22c55e")
            status_text = "OUT OF STOCK" if qty == 0 else ("LOW STOCK" if is_low else "In Stock")

            col1, col2, col3, col4 = st.columns([3, 1, 1, 2])
            with col1:
                st.markdown(f"**{med_name}** | {med.get('strength', '')}")
                st.caption(f"{med.get('category', '')} | {med.get('dosage_form', '')}")
            with col2:
                st.markdown(f"<span style='color:{color};font-weight:700;'>{qty}</span>", unsafe_allow_html=True)
                st.caption("Available")
            with col3:
                st.markdown(f"₹{inv.get('selling_price', 0)}")
                st.caption("Price")
            with col4:
                new_qty = st.number_input("Update Qty", min_value=0, value=qty, key=f"inv_qty_{inv['id']}", label_visibility="collapsed")
                if new_qty != qty:
                    if st.button("Update", key=f"inv_update_{inv['id']}"):
                        db.update_inventory(inv["id"], {"quantity_available": new_qty})
                        st.success(f"{med_name} updated to {new_qty}")
                        st.rerun()
            st.markdown("---")

    except Exception as e:
        st.error(f"Error loading inventory: {e}")

    # Add new medicine
    with st.expander("Add New Medicine to Catalog"):
        with st.form("add_medicine_form"):
            acol1, acol2 = st.columns(2)
            with acol1:
                new_med_name = st.text_input("Medicine Name")
                new_generic = st.text_input("Generic Name")
                new_category = st.text_input("Category", placeholder="e.g., Antibiotic")
            with acol2:
                new_form = st.selectbox("Dosage Form", ["Tablet", "Capsule", "Syrup", "Injection", "Inhaler", "Gel", "Drops", "Powder"])
                new_strength = st.text_input("Strength", placeholder="e.g., 500mg")
                new_price = st.number_input("Unit Price (₹)", min_value=0.0, value=10.0)

            if st.form_submit_button("Add Medicine", use_container_width=True):
                if new_med_name:
                    db.create_medicine({
                        "name": new_med_name,
                        "generic_name": new_generic,
                        "category": new_category,
                        "dosage_form": new_form,
                        "strength": new_strength,
                        "unit_price": new_price,
                    })
                    st.success(f"{new_med_name} added.")
                    st.rerun()


# ══════════════════════════════════════════════════════════════
# TAB 3: Substitutions
# ══════════════════════════════════════════════════════════════
elif active_tab == "Substitutions":
    st.markdown("### AI-Suggested Substitutions")
    st.info("Review and approve medicine substitutions suggested by AI. No substitution happens automatically.")

    try:
        pending = db.get_pending_prescriptions()

        has_substitutions = False
        for rx in pending:
            items = rx.get("prescription_items", [])
            for item in items:
                if item.get("is_in_stock") is False and not item.get("substitute_approved"):
                    has_substitutions = True

                    patient_info = rx.get("patients", {}) or {}
                    p_user = patient_info.get("users", {}) or {}

                    st.markdown(f"""
                    ##### {item.get('medicine_name', 'N/A')} — Out of Stock
                    **Patient:** {p_user.get('full_name', 'Unknown')} | **Rx:** {rx.get('prescription_code', 'N/A')}
                    """)

                    # Find alternatives
                    if item.get("medicine_id"):
                        alternatives = db.get_medicine_alternatives(item["medicine_id"])
                        if alternatives:
                            st.markdown("**Available Alternatives:**")
                            for alt in alternatives:
                                alt_stock = db.check_medicine_stock(alt["id"])
                                alt_qty = alt_stock.get("quantity_available", 0) if alt_stock else 0

                                col1, col2 = st.columns([3, 1])
                                with col1:
                                    st.markdown(f"{alt['name']} ({alt.get('generic_name', 'N/A')}) — Available: {alt_qty}")
                                with col2:
                                    if alt_qty > 0:
                                        if st.button("Approve", key=f"approve_{item['id']}_{alt['id']}"):
                                            approve_substitute(item["id"], alt["id"], profile["id"])
                                            st.success(f"Substitute approved: {alt['name']}")
                                            st.rerun()
                        else:
                            st.warning("No alternatives found in inventory.")
                    st.markdown("---")

        if not has_substitutions:
            st.success("No pending substitution reviews.")

    except Exception as e:
        st.error(f"Error: {e}")


# ══════════════════════════════════════════════════════════════
# TAB 4: Dispense Medicines
# ══════════════════════════════════════════════════════════════
elif active_tab == "Dispense":
    st.markdown("### Dispensing History")
    st.info("Recent prescriptions dispensed by the pharmacy.")

    try:
        # Get recent audit entries for dispensing
        audit = db.get_audit_log(limit=50, entity_type="prescription")
        dispensed = [a for a in audit if a.get("action") == "prescription_dispensed"]

        if dispensed:
            for entry in dispensed[:20]:
                user_info = entry.get("users", {}) or {}
                st.markdown(f"""
                **Dispensed** — {entry.get('created_at', 'N/A')[:16]}
                | By: {user_info.get('full_name', 'Unknown')}
                | Rx ID: `{entry.get('entity_id', 'N/A')[:8]}...`
                """)
                st.markdown("---")
        else:
            st.info("No dispensing history yet.")
    except Exception as e:
        st.error(f"Error: {e}")
