"""
MediFlow AI — Queue Manager Agent (Pipeline A)
================================================
Handles doctor-patient matching and queue token assignment.
Checks real-time doctor availability, assigns optimal queue slots,
and estimates wait times.
"""

import logging
from datetime import date
from typing import Optional
from database import queries as db
from utils.helpers import generate_token_number, estimate_wait_time

logger = logging.getLogger(__name__)


def find_best_doctor(
    department_name: str,
    urgency: str = "routine",
) -> dict:
    """
    Find the best available doctor for a given department and urgency.

    Strategy:
    1. Get all available doctors in the recommended department
    2. Sort by current queue length (shortest queue first)
    3. For emergencies, find doctor with shortest queue regardless
    4. Return best match or None if no doctors available

    Returns:
        dict with doctor info, or None if no doctor available
    """
    try:
        # Get department
        department = db.get_department_by_name(department_name)
        if not department:
            logger.warning(f"Department not found: {department_name}")
            return None

        # Get available doctors in this department
        available_doctors = db.get_available_doctors(department["id"])

        if not available_doctors:
            # For emergencies, check ANY available doctor
            if urgency == "emergency":
                all_available = db.get_available_doctors()
                if all_available:
                    logger.info("No doctors in requested department. Routing emergency to any available doctor.")
                    # Sort by queue length
                    for doc in all_available:
                        doc["_queue_size"] = db.get_queue_position(doc["id"])
                    all_available.sort(key=lambda d: d["_queue_size"])
                    return _format_doctor_result(all_available[0], department)
            return None

        # Calculate queue sizes for each doctor
        for doc in available_doctors:
            doc["_queue_size"] = db.get_queue_position(doc["id"])

        # Sort by queue length (shortest first)
        available_doctors.sort(key=lambda d: d["_queue_size"])

        # Check if any doctor hasn't reached max capacity
        for doc in available_doctors:
            max_patients = doc.get("max_daily_patients", 30)
            if doc["_queue_size"] < max_patients:
                return _format_doctor_result(doc, department)

        # All doctors at capacity — return the one with shortest queue anyway
        logger.warning(f"All doctors in {department_name} at capacity. Assigning to shortest queue.")
        return _format_doctor_result(available_doctors[0], department)

    except Exception as e:
        logger.error(f"Error finding best doctor: {e}")
        return None


def _format_doctor_result(doctor: dict, department: dict) -> dict:
    """Format doctor data for queue assignment."""
    user_info = doctor.get("users", {}) or {}
    dept_info = doctor.get("departments", {}) or {}
    queue_size = doctor.get("_queue_size", 0)
    wait = estimate_wait_time(queue_size)

    return {
        "doctor_id": doctor["id"],
        "doctor_name": user_info.get("full_name", "Doctor"),
        "department_id": department["id"] if department else doctor.get("department_id"),
        "department_name": dept_info.get("name", department.get("name", "Unknown")),
        "specialization": doctor.get("specialization", ""),
        "queue_position": queue_size + 1,
        "estimated_wait": wait["display"],
        "estimated_wait_minutes": wait["total_minutes"],
        "consultation_fee": doctor.get("consultation_fee", 0),
    }


def assign_queue_token(
    patient_id: str,
    doctor_id: str,
    department_id: str,
    urgency: str = "routine",
    symptom_summary: str = "",
    ai_recommended_department: str = "",
    ai_urgency_score: str = "",
    ai_confidence: float = 0,
) -> dict:
    """
    Assign a queue token to a patient for a specific doctor.

    Creates the appointment record in the database and returns
    the token details.
    """
    try:
        # Get current queue position
        queue_position = db.get_queue_position(doctor_id) + 1

        # Get department name for token
        department = db.get_department_by_id(department_id)
        dept_name = department["name"] if department else "General Medicine"

        # Generate token number
        token_number = generate_token_number(dept_name, queue_position)

        # Calculate estimated time
        wait = estimate_wait_time(queue_position - 1)

        # Create appointment record
        appointment_data = {
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "department_id": department_id,
            "token_number": token_number,
            "queue_position": queue_position,
            "urgency": urgency,
            "symptom_summary": symptom_summary,
            "ai_recommended_department": ai_recommended_department,
            "ai_urgency_score": ai_urgency_score,
            "ai_confidence": ai_confidence,
            "scheduled_date": date.today().isoformat(),
            "status": "waiting",
        }

        result = db.create_appointment(appointment_data)

        if result:
            appointment = result[0] if isinstance(result, list) else result

            # Create initial workflow state
            db.create_workflow_state({
                "appointment_id": appointment["id"],
                "patient_id": patient_id,
                "current_state": "registered",
                "previous_state": None,
                "notes": f"Registered via AI intake. Department: {dept_name}",
            })

            # Create audit log entry
            db.create_audit_entry({
                "action": "queue_token_assigned",
                "entity_type": "appointment",
                "entity_id": appointment["id"],
                "details": {
                    "token": token_number,
                    "department": dept_name,
                    "urgency": urgency,
                    "queue_position": queue_position,
                    "ai_confidence": ai_confidence,
                },
                "ai_model_used": ai_recommended_department,
                "ai_confidence": ai_confidence,
            })

            logger.info(f"Queue token assigned: {token_number} (position {queue_position})")

            return {
                "success": True,
                "appointment_id": appointment["id"],
                "token_number": token_number,
                "queue_position": queue_position,
                "estimated_wait": wait["display"],
                "estimated_wait_minutes": wait["total_minutes"],
                "department": dept_name,
                "message": f"Token {token_number} assigned. Estimated wait: {wait['display']}",
            }

        return {"success": False, "message": "Failed to create appointment."}

    except Exception as e:
        logger.error(f"Error assigning queue token: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


def get_patient_queue_status(patient_id: str) -> list:
    """
    Get the current queue status for a patient (all active appointments today).
    """
    try:
        appointments = db.get_appointments_by_patient(patient_id, status="waiting")
        results = []
        for appt in appointments:
            # Get fresh queue position
            current_position = db.get_queue_position(appt["doctor_id"])
            my_position = appt.get("queue_position", 0)
            ahead = max(0, my_position - (appt["doctor_id"] and 1 or 0))

            doctor_info = appt.get("doctors", {}) or {}
            user_info = doctor_info.get("users", {}) or {}
            dept_info = appt.get("departments", {}) or {}

            wait = estimate_wait_time(ahead)

            results.append({
                "appointment_id": appt["id"],
                "token_number": appt["token_number"],
                "queue_position": my_position,
                "people_ahead": ahead,
                "estimated_wait": wait["display"],
                "department": dept_info.get("name", "Unknown"),
                "doctor_name": user_info.get("full_name", "Doctor"),
                "status": appt["status"],
                "urgency": appt["urgency"],
            })

        return results

    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return []
