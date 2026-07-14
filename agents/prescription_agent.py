"""
MediFlow AI — Prescription Processing Agent (Pipeline B)
=========================================================
Processes structured prescription data from doctors,
validates medicine names against the catalog, and formats
prescriptions for pharmacy routing.
"""

import json
import logging
from typing import List, Optional
from database import queries as db
from agents.llm_client import get_llm_client
from utils.helpers import generate_prescription_id

logger = logging.getLogger(__name__)


PRESCRIPTION_VALIDATION_PROMPT = """You are MediFlow AI's Prescription Validation Assistant. Your role is to review a doctor's prescription for completeness and potential issues.

PRESCRIPTION ITEMS:
{prescription_items}

PATIENT INFO:
- Known Allergies: {allergies}
- Chronic Conditions: {chronic_conditions}
- Current Medications: {current_meds}

Review each prescription item and check for:
1. Reasonable dosage for the given medicine
2. Potential drug interactions between prescribed medicines
3. Allergy conflicts with patient's known allergies
4. Contraindications with chronic conditions
5. Completeness of instructions

Respond ONLY with valid JSON:
{{
    "is_valid": true,
    "warnings": ["list of any warnings or concerns"],
    "interactions": ["list of any potential drug interactions"],
    "allergy_alerts": ["list of any allergy-related concerns"],
    "suggestions": ["list of any improvement suggestions"]
}}"""


def process_prescription(
    consultation_id: str,
    patient_id: str,
    doctor_id: str,
    doctor_user_id: str,
    items: List[dict],
    patient_allergies: Optional[list] = None,
    patient_conditions: Optional[list] = None,
) -> dict:
    """
    Process a new prescription from a doctor.

    Steps:
    1. Generate unique prescription code
    2. Validate items against medicine catalog
    3. Run AI validation for interactions/allergies
    4. Create prescription and items in database
    5. Route to pharmacy for stock check

    Args:
        consultation_id: ID of the consultation
        patient_id: Patient's record ID
        doctor_id: Prescribing doctor's record ID
        items: List of prescription item dicts
        patient_allergies: Known allergies
        patient_conditions: Known chronic conditions

    Returns:
        dict with prescription details and validation results
    """
    try:
        # Generate prescription code
        prescription_code = generate_prescription_id()

        # Match items to medicine catalog
        matched_items = []
        for item in items:
            medicine_name = item.get("medicine_name", "")
            # Search medicine catalog
            matches = db.search_medicines(medicine_name)
            medicine_id = matches[0]["id"] if matches else None

            matched_items.append({
                "medicine_name": medicine_name,
                "medicine_id": medicine_id,
                "dosage": item.get("dosage", ""),
                "frequency": item.get("frequency", ""),
                "duration": item.get("duration", ""),
                "route": item.get("route", "Oral"),
                "quantity": item.get("quantity", 1),
                "instructions": item.get("instructions", ""),
            })

        # AI validation (non-blocking — prescription goes through even if AI fails)
        validation_result = _validate_prescription_ai(
            matched_items, patient_allergies, patient_conditions
        )

        # Create prescription in database
        prescription_data = {
            "prescription_code": prescription_code,
            "consultation_id": consultation_id,
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "status": "created",
        }
        rx_result = db.create_prescription(prescription_data)

        if not rx_result:
            return {"success": False, "message": "Failed to create prescription record."}

        prescription = rx_result[0] if isinstance(rx_result, list) else rx_result
        prescription_id = prescription["id"]

        # Create prescription items
        db_items = []
        for item in matched_items:
            db_items.append({
                "prescription_id": prescription_id,
                "medicine_id": item["medicine_id"],
                "medicine_name": item["medicine_name"],
                "dosage": item["dosage"],
                "frequency": item["frequency"],
                "duration": item["duration"],
                "route": item["route"],
                "quantity": item["quantity"],
                "instructions": item["instructions"],
            })

        db.create_prescription_items(db_items)

        # Create audit log
        db.create_audit_entry({
            "actor_id": doctor_user_id,
            "actor_role": "doctor",
            "action": "prescription_created",
            "entity_type": "prescription",
            "entity_id": prescription_id,
            "details": {
                "prescription_code": prescription_code,
                "item_count": len(db_items),
                "validation": validation_result,
            },
        })

        logger.info(f"Prescription created: {prescription_code} ({len(db_items)} items)")

        return {
            "success": True,
            "prescription_id": prescription_id,
            "prescription_code": prescription_code,
            "item_count": len(db_items),
            "validation": validation_result,
            "message": f"Prescription {prescription_code} created with {len(db_items)} items.",
        }

    except Exception as e:
        logger.error(f"Error processing prescription: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


def _validate_prescription_ai(
    items: list,
    allergies: Optional[list],
    conditions: Optional[list],
) -> dict:
    """Run AI validation on prescription items (non-blocking)."""
    try:
        llm_client = get_llm_client()

        items_text = "\n".join(
            f"- {item['medicine_name']} {item['dosage']} | {item['frequency']} | {item['duration']} | Route: {item['route']}"
            for item in items
        )

        system_prompt = PRESCRIPTION_VALIDATION_PROMPT.format(
            prescription_items=items_text,
            allergies=", ".join(allergies) if allergies else "None known",
            chronic_conditions=", ".join(conditions) if conditions else "None known",
            current_meds="Not available",
        )

        response = llm_client.invoke_json(system_prompt, "Please validate this prescription.")

        # Clean and parse
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()

        return json.loads(response)

    except Exception as e:
        logger.warning(f"AI prescription validation failed (non-blocking): {e}")
        return {
            "is_valid": True,
            "warnings": ["AI validation unavailable — manual review recommended"],
            "interactions": [],
            "allergy_alerts": [],
            "suggestions": [],
        }


def send_to_pharmacy(prescription_id: str) -> dict:
    """
    Route a prescription to the pharmacy for stock checking and dispensing.
    Updates prescription status to 'sent_to_pharmacy'.
    """
    try:
        db.update_prescription(prescription_id, {"status": "sent_to_pharmacy"})

        # Create notification for pharmacists
        pharmacists = db.get_users_by_role("pharmacist")
        for pharmacist in pharmacists:
            db.create_notification({
                "user_id": pharmacist["id"],
                "type": "prescription_ready",
                "title": "New Prescription Received",
                "message": f"A new prescription is ready for processing.",
                "metadata": {"prescription_id": prescription_id},
            })

        logger.info(f"Prescription {prescription_id} sent to pharmacy.")
        return {"success": True, "message": "Prescription sent to pharmacy."}

    except Exception as e:
        logger.error(f"Error sending prescription to pharmacy: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}
