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


PRESCRIPTION_VALIDATION_PROMPT = """You are MediFlow AI's Prescription Validation Assistant. Your role is to review a doctor's prescription for completeness, potential issues, and stock availability.

PRESCRIPTION ITEMS:
{prescription_items}

PATIENT INFO:
- Known Allergies: {allergies}
- Chronic Conditions: {chronic_conditions}
- Current Medications: {current_meds}

AVAILABLE PHARMACY INVENTORY:
{inventory_list}

Review each prescription item and check for:
1. Reasonable dosage and correct route of administration for the given medicine (e.g., do not inhale an oral tablet).
2. Potential drug interactions between prescribed medicines.
3. Allergy conflicts with patient's known allergies.
4. Contraindications with chronic conditions.
5. Completeness of instructions.
6. Stock availability: If a prescribed medication is out of stock (Stock: 0), you MUST add a warning about this in the "warnings" array to prevent the prescription from proceeding. Also, actively search the AVAILABLE PHARMACY INVENTORY and recommend a suitable, in-stock alternative in the "suggestions" array.

Respond ONLY with valid JSON:
{{
    "is_valid": true,
    "warnings": ["list of any warnings, dosage errors, inappropriate routes, OR out of stock medicines"],
    "interactions": ["list of any potential drug interactions"],
    "allergy_alerts": ["list of any allergy-related concerns"],
    "suggestions": ["list of any improvement suggestions, INCLUDING specific alternative medicines from the inventory if needed"]
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

        # AI validation (Blocking — Prescription is rejected if there are warnings)
        validation_result = _validate_prescription_ai(
            matched_items, patient_allergies, patient_conditions
        )
        
        has_critical_errors = (
            len(validation_result.get("warnings", [])) > 0 or
            len(validation_result.get("interactions", [])) > 0 or
            len(validation_result.get("allergy_alerts", [])) > 0
        )
        
        if has_critical_errors:
            logger.warning(f"Prescription rejected by AI validation for patient {patient_id}")
            return {
                "success": False, 
                "message": "AI validation failed. Please review the warnings.",
                "validation": validation_result
            }

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
        
        # Fetch current pharmacy inventory for suggestions
        try:
            inventory = db.get_pharmacy_inventory()
            inventory_text = "\n".join(
                f"- {i.get('medicines', {}).get('name', 'Unknown')} ({i.get('medicines', {}).get('category', 'N/A')}) - Stock: {i.get('quantity_available', 0)}"
                for i in inventory
            )
            if not inventory_text:
                inventory_text = "No inventory data available."
        except Exception as e:
            logger.error(f"Failed to fetch inventory for validation: {e}")
            inventory_text = "Inventory check failed."

        system_prompt = PRESCRIPTION_VALIDATION_PROMPT.format(
            prescription_items=items_text,
            allergies=", ".join(allergies) if allergies else "None known",
            chronic_conditions=", ".join(conditions) if conditions else "None known",
            current_meds="Not available",
            inventory_list=inventory_text,
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
        logger.error(f"Error sending to pharmacy: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


def generate_prescription_from_consult(consult_data: dict) -> list:
    """
    Generate a prescription automatically based on the doctor's consultation report.
    Picks medications strictly from the available pharmacy inventory.
    """
    try:
        # Fetch current pharmacy inventory for suggestions
        try:
            inventory = db.get_pharmacy_inventory()
            inventory_text = "\n".join(
                f"- {i.get('medicines', {}).get('name', 'Unknown')} ({i.get('medicines', {}).get('category', 'N/A')}) - Stock: {i.get('quantity_available', 0)}"
                for i in inventory if i.get('quantity_available', 0) > 0
            )
            if not inventory_text:
                inventory_text = "No inventory data available."
        except Exception as e:
            logger.error(f"Failed to fetch inventory for generation: {e}")
            inventory_text = "Inventory check failed."
            
        system_prompt = f"""You are MediFlow AI's Clinical Pharmacologist.
Based on the following doctor's consultation report, generate a complete prescription.

CONSULTATION DETAILS:
- Symptoms: {consult_data.get('symptoms', 'None')}
- Diagnosis: {consult_data.get('diagnosis', 'None')}
- Examination Notes: {consult_data.get('examination_notes', 'None')}
- Additional Notes: {consult_data.get('additional_notes', 'None')}

AVAILABLE PHARMACY INVENTORY (You MUST strictly choose from these medicines ONLY):
{inventory_text}

INSTRUCTIONS:
Generate a list of prescribed medications. Ensure that:
- You ONLY pick medicines that are IN STOCK in the inventory above.
- Dosages, routes, frequencies, and durations are clinically appropriate.

Respond ONLY with valid JSON in this exact format:
{{
    "prescription_items": [
        {{
            "medicine_name": "Exact Name from Inventory",
            "dosage": "e.g., 500mg",
            "frequency": "Once daily (OD)", 
            "duration": "5 days",
            "route": "Oral",
            "quantity": 10,
            "instructions": "Take after meals"
        }}
    ]
}}
Note: For frequency, use one of: ["Once daily (OD)", "Twice daily (BD)", "Three times daily (TDS)", "Four times daily (QDS)", "As needed (PRN)", "Immediately (STAT)"]
Note: For route, use one of: ["Oral", "Intravenous", "Intramuscular", "Subcutaneous", "Topical", "Inhalation", "Drops", "Other"]
"""
        llm_client = get_llm_client()
        response = llm_client.invoke_json(system_prompt, "Generate prescription items based on consultation.")
        
        response = response.strip()
        if response.startswith("```"):
            response = response.split("\n", 1)[1]
            if response.endswith("```"):
                response = response[:-3]
            response = response.strip()
            
        result = json.loads(response)
        return result.get("prescription_items", [])
    except Exception as e:
        logger.error(f"Failed to generate prescription from consult: {e}")
        return []
