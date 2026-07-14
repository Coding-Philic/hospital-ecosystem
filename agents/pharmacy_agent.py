"""
MediFlow AI — Pharmacy Matching Agent (Pipeline B)
====================================================
Checks prescribed medicines against pharmacy inventory.
If in stock → auto-routes to pharmacy queue.
If out of stock → suggests generic/therapeutic alternatives.

IMPORTANT: Drug substitution is NEVER automatic.
Alternatives are flagged for pharmacist/doctor approval.
"""

import json
import logging
from typing import List, Optional
from database import queries as db
from agents.llm_client import get_llm_client

logger = logging.getLogger(__name__)

ALTERNATIVE_SUGGESTION_PROMPT = """You are MediFlow AI's Pharmacy Assistant. A prescribed medicine is OUT OF STOCK.
Suggest safe generic or therapeutic alternatives.

OUT OF STOCK MEDICINE:
- Name: {medicine_name}
- Generic Name: {generic_name}
- Dosage Form: {dosage_form}
- Strength: {strength}
- Category: {category}

AVAILABLE ALTERNATIVES IN INVENTORY:
{available_alternatives}

PATIENT ALLERGIES: {allergies}

IMPORTANT: You are suggesting alternatives for a licensed pharmacist to review.
Never recommend alternatives that conflict with known allergies.

Respond ONLY with valid JSON:
{{
    "suggested_alternatives": [
        {{
            "medicine_name": "name",
            "reason": "why this is a suitable alternative",
            "is_generic_equivalent": true
        }}
    ],
    "notes_for_pharmacist": "any additional notes"
}}"""


def check_prescription_stock(prescription_id: str, patient_allergies: Optional[list] = None) -> dict:
    """
    Check all items in a prescription against pharmacy inventory.

    Returns stock status for each item:
    - In stock: ready for dispensing
    - Out of stock: AI-suggested alternatives (pending approval)
    - Low stock: available but flagged for reorder

    Args:
        prescription_id: The prescription to check
        patient_allergies: Patient's known allergies for safety filtering

    Returns:
        dict with overall status and per-item details
    """
    try:
        # Get prescription with items
        prescriptions = db.get_pending_prescriptions()
        prescription = None
        for rx in prescriptions:
            if rx["id"] == prescription_id:
                prescription = rx
                break

        if not prescription:
            return {"success": False, "message": "Prescription not found."}

        items = prescription.get("prescription_items", [])
        if not items:
            return {"success": False, "message": "No items in prescription."}

        stock_results = []
        all_in_stock = True
        partially_available = False

        for item in items:
            medicine_id = item.get("medicine_id")
            medicine_name = item.get("medicine_name", "Unknown")
            required_qty = item.get("quantity", 1)

            if medicine_id:
                # Check inventory
                stock = db.check_medicine_stock(medicine_id)

                if stock and stock.get("quantity_available", 0) >= required_qty:
                    # In stock
                    stock_results.append({
                        "item_id": item["id"],
                        "medicine_name": medicine_name,
                        "status": "in_stock",
                        "quantity_available": stock["quantity_available"],
                        "quantity_required": required_qty,
                        "alternatives": [],
                    })
                    partially_available = True

                    # Update item status
                    db.update_prescription_item(item["id"], {"is_in_stock": True})

                else:
                    # Out of stock — find alternatives
                    all_in_stock = False
                    alternatives = _find_alternatives(
                        medicine_id, medicine_name, patient_allergies
                    )

                    stock_results.append({
                        "item_id": item["id"],
                        "medicine_name": medicine_name,
                        "status": "out_of_stock",
                        "quantity_available": stock.get("quantity_available", 0) if stock else 0,
                        "quantity_required": required_qty,
                        "alternatives": alternatives,
                    })

                    db.update_prescription_item(item["id"], {"is_in_stock": False})
            else:
                # Medicine not in catalog
                all_in_stock = False
                stock_results.append({
                    "item_id": item["id"],
                    "medicine_name": medicine_name,
                    "status": "not_in_catalog",
                    "quantity_available": 0,
                    "quantity_required": required_qty,
                    "alternatives": [],
                })
                db.update_prescription_item(item["id"], {"is_in_stock": False})

        # Update prescription status
        if all_in_stock:
            new_status = "sent_to_pharmacy"
        elif partially_available:
            new_status = "partially_available"
        else:
            new_status = "sent_to_pharmacy"

        db.update_prescription(prescription_id, {"status": new_status})

        logger.info(
            f"Stock check for {prescription_id}: "
            f"{'All in stock' if all_in_stock else 'Some items unavailable'}"
        )

        return {
            "success": True,
            "prescription_id": prescription_id,
            "all_in_stock": all_in_stock,
            "status": new_status,
            "items": stock_results,
            "message": "All items available" if all_in_stock else "Some items need alternatives",
        }

    except Exception as e:
        logger.error(f"Error checking prescription stock: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


def _find_alternatives(
    medicine_id: str,
    medicine_name: str,
    patient_allergies: Optional[list] = None,
) -> list:
    """Find alternative medicines using database and AI assistance."""
    alternatives = []

    try:
        # First, check database for pre-approved alternatives
        db_alternatives = db.get_medicine_alternatives(medicine_id)

        for alt in db_alternatives:
            # Check if alternative is in stock
            alt_stock = db.check_medicine_stock(alt["id"])
            if alt_stock and alt_stock.get("quantity_available", 0) > 0:
                alternatives.append({
                    "medicine_id": alt["id"],
                    "medicine_name": alt["name"],
                    "generic_name": alt.get("generic_name", ""),
                    "strength": alt.get("strength", ""),
                    "quantity_available": alt_stock["quantity_available"],
                    "is_generic_equivalent": alt.get("generic_name") == db.get_medicine_by_id(medicine_id).get("generic_name"),
                    "source": "database",
                    "requires_approval": True,
                })

        # If no database alternatives, use AI to suggest from available inventory
        if not alternatives:
            try:
                medicine = db.get_medicine_by_id(medicine_id)
                if medicine:
                    all_medicines = db.get_all_medicines()
                    available_names = [
                        f"- {m['name']} ({m.get('generic_name', 'N/A')}) | {m.get('category', '')} | {m.get('strength', '')}"
                        for m in all_medicines
                        if m["id"] != medicine_id
                    ]

                    llm_client = get_llm_client()
                    system_prompt = ALTERNATIVE_SUGGESTION_PROMPT.format(
                        medicine_name=medicine.get("name", medicine_name),
                        generic_name=medicine.get("generic_name", "Unknown"),
                        dosage_form=medicine.get("dosage_form", "Unknown"),
                        strength=medicine.get("strength", "Unknown"),
                        category=medicine.get("category", "Unknown"),
                        available_alternatives="\n".join(available_names[:20]),
                        allergies=", ".join(patient_allergies) if patient_allergies else "None known",
                    )

                    response = llm_client.invoke_json(system_prompt, "Suggest alternatives.")
                    response = response.strip()
                    if response.startswith("```"):
                        response = response.split("\n", 1)[1]
                        if response.endswith("```"):
                            response = response[:-3]
                        response = response.strip()

                    ai_result = json.loads(response)

                    for suggestion in ai_result.get("suggested_alternatives", []):
                        alternatives.append({
                            "medicine_name": suggestion.get("medicine_name", ""),
                            "reason": suggestion.get("reason", ""),
                            "is_generic_equivalent": suggestion.get("is_generic_equivalent", False),
                            "source": "ai_suggestion",
                            "requires_approval": True,
                        })

            except Exception as e:
                logger.warning(f"AI alternative suggestion failed: {e}")

    except Exception as e:
        logger.error(f"Error finding alternatives: {e}")

    return alternatives


def dispense_prescription(prescription_id: str, pharmacist_user_id: str) -> dict:
    """
    Mark a prescription as dispensed and update inventory.

    Args:
        prescription_id: The prescription to dispense
        pharmacist_user_id: The pharmacist dispensing the medicine

    Returns:
        dict with success status
    """
    try:
        # Update prescription status
        from datetime import datetime
        db.update_prescription(prescription_id, {
            "status": "dispensed",
            "dispensed_by": pharmacist_user_id,
            "dispensed_at": datetime.now().isoformat(),
        })

        # TODO: Deduct from inventory (would need prescription items + inventory mapping)

        # Get patient for notification
        prescriptions = db.get_pending_prescriptions()
        patient_user_id = None
        for rx in prescriptions:
            if rx["id"] == prescription_id:
                patient_info = rx.get("patients", {})
                if patient_info:
                    patient_user_info = patient_info.get("users", {})
                    # We need the user_id from patients table
                    break

        # Create audit log
        db.create_audit_entry({
            "actor_id": pharmacist_user_id,
            "actor_role": "pharmacist",
            "action": "prescription_dispensed",
            "entity_type": "prescription",
            "entity_id": prescription_id,
        })

        logger.info(f"Prescription {prescription_id} dispensed by {pharmacist_user_id}")
        return {"success": True, "message": "Prescription dispensed successfully."}

    except Exception as e:
        logger.error(f"Error dispensing prescription: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


def approve_substitute(
    item_id: str,
    substitute_medicine_id: str,
    approved_by: str,
) -> dict:
    """
    Approve a medicine substitution (pharmacist or doctor action).

    Args:
        item_id: Prescription item ID
        substitute_medicine_id: The approved substitute medicine ID
        approved_by: User ID of the approving professional

    Returns:
        dict with success status
    """
    try:
        db.update_prescription_item(item_id, {
            "substitute_medicine_id": substitute_medicine_id,
            "substitute_approved_by": approved_by,
            "substitute_approved": True,
        })

        db.create_audit_entry({
            "actor_id": approved_by,
            "action": "substitute_approved",
            "entity_type": "prescription_item",
            "entity_id": item_id,
            "details": {"substitute_medicine_id": substitute_medicine_id},
        })

        logger.info(f"Substitute approved for item {item_id}")
        return {"success": True, "message": "Substitute approved."}

    except Exception as e:
        logger.error(f"Error approving substitute: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}
