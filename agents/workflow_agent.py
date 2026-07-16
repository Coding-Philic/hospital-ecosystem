"""
MediFlow AI — Workflow State Machine Agent (Pipeline C)
========================================================
Manages the patient's journey through the hospital as a state machine.

States: registered → triaged → queued → in_consultation →
        investigation_ordered → investigation_complete →
        prescribed → at_pharmacy → dispensed → billing → discharged

Each transition is logged with timestamp and responsible person.
Invalid transitions are rejected.
"""

import logging
from datetime import datetime
from typing import Optional
from config import config
from database import queries as db

logger = logging.getLogger(__name__)

# ── Valid State Transitions ───────────────────────────────────
# Defines which states can transition to which other states
VALID_TRANSITIONS = {
    "registered": ["triaged", "queued", "discharged"],  # Can skip triage if walk-in
    "triaged": ["queued", "discharged"],
    "queued": ["in_consultation", "discharged", "registered"],  # Can go back if cancelled
    "in_consultation": ["investigation_ordered", "prescribed", "billing", "discharged"],
    "investigation_ordered": ["investigation_complete"],
    "investigation_complete": ["in_consultation", "prescribed"],  # Back to doctor with results
    "prescribed": ["at_pharmacy", "dispensed", "billing", "discharged"],  # Can discharge if no pharmacy needed
    "at_pharmacy": ["dispensed"],
    "dispensed": ["billing", "discharged"],
    "billing": ["discharged"],
    "discharged": [],  # Terminal state
}


def transition_state(
    appointment_id: str,
    patient_id: str,
    new_state: str,
    transitioned_by: Optional[str] = None,
    transitioned_by_role: Optional[str] = None,
    notes: str = "",
    metadata: Optional[dict] = None,
) -> dict:
    """
    Transition a patient's workflow to a new state.

    Validates the transition, logs it, and notifies relevant parties.

    Args:
        appointment_id: The appointment being tracked
        patient_id: The patient's record ID
        new_state: The target workflow state
        transitioned_by: User ID of the person making the transition
        transitioned_by_role: Role of the person (doctor, receptionist, etc.)
        notes: Optional notes about the transition
        metadata: Optional metadata dict

    Returns:
        dict with success status and current state info
    """
    try:
        # Get current state
        current = db.get_current_workflow_state(appointment_id)

        if current:
            current_state = current["current_state"]
        else:
            # No workflow state exists yet — this is the first transition
            current_state = None

        # Validate transition
        if current_state and new_state not in VALID_TRANSITIONS.get(current_state, []):
            logger.warning(
                f"Invalid workflow transition: {current_state} → {new_state} "
                f"(appointment: {appointment_id})"
            )
            return {
                "success": False,
                "message": f"Invalid transition: cannot move from '{current_state}' to '{new_state}'.",
                "current_state": current_state,
                "valid_transitions": VALID_TRANSITIONS.get(current_state, []),
            }

        # Create workflow state entry
        state_data = {
            "appointment_id": appointment_id,
            "patient_id": patient_id,
            "current_state": new_state,
            "previous_state": current_state,
            "transitioned_by": transitioned_by,
            "transitioned_by_role": transitioned_by_role,
            "notes": notes,
            "metadata": metadata or {},
        }

        db.create_workflow_state(state_data)

        # Update appointment status based on workflow state
        appointment_status_map = {
            "queued": "waiting",
            "in_consultation": "in_progress",
            "discharged": "completed",
        }
        if new_state in appointment_status_map:
            appt_update = {"status": appointment_status_map[new_state]}
            if new_state == "in_consultation":
                appt_update["consultation_start_time"] = datetime.now().astimezone().isoformat()
            elif new_state == "discharged":
                appt_update["consultation_end_time"] = datetime.now().astimezone().isoformat()
            db.update_appointment(appointment_id, appt_update)

        # Create audit entry
        db.create_audit_entry({
            "actor_id": transitioned_by,
            "actor_role": transitioned_by_role,
            "action": "workflow_transition",
            "entity_type": "appointment",
            "entity_id": appointment_id,
            "details": {
                "from_state": current_state,
                "to_state": new_state,
                "notes": notes,
            },
        })

        # Send notification to patient
        _notify_patient_state_change(patient_id, new_state, notes)

        logger.info(f"Workflow transition: {current_state} → {new_state} (appointment: {appointment_id})")

        return {
            "success": True,
            "previous_state": current_state,
            "current_state": new_state,
            "message": f"Workflow updated: {_state_label(current_state)} → {_state_label(new_state)}",
        }

    except Exception as e:
        logger.error(f"Error in workflow transition: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


def get_workflow_timeline(appointment_id: str) -> list:
    """
    Get the complete workflow timeline for an appointment.
    Returns a chronological list of all state transitions.
    """
    try:
        history = db.get_workflow_history(appointment_id)

        timeline = []
        for entry in history:
            user_info = entry.get("users", {}) or {}
            timeline.append({
                "state": entry["current_state"],
                "previous_state": entry.get("previous_state"),
                "label": _state_label(entry["current_state"]),
                "timestamp": entry["created_at"],
                "transitioned_by": user_info.get("full_name", "System"),
                "role": entry.get("transitioned_by_role", "system"),
                "notes": entry.get("notes", ""),
            })

        return timeline

    except Exception as e:
        logger.error(f"Error getting workflow timeline: {e}")
        return []


def get_current_state(appointment_id: str) -> str:
    """Get the current workflow state for an appointment."""
    try:
        current = db.get_current_workflow_state(appointment_id)
        return current["current_state"] if current else "registered"
    except Exception:
        return "registered"


def get_valid_next_states(current_state: str) -> list:
    """Get the valid next states from the current state."""
    return VALID_TRANSITIONS.get(current_state, [])


def _state_label(state: Optional[str]) -> str:
    """Get a human-readable label for a workflow state."""
    from utils.constants import WORKFLOW_DISPLAY
    if not state:
        return "New"
    display = WORKFLOW_DISPLAY.get(state, {})
    return f"{display.get('label', state)}"


def _notify_patient_state_change(patient_id: str, new_state: str, notes: str = ""):
    """Send a notification to the patient about their workflow state change."""
    try:
        # Get patient's user_id
        patient = db.get_patient_by_user_id(patient_id)
        if not patient:
            # patient_id might be the patients table ID, not user_id
            # In that case, we can't easily get the user_id without a query
            return

        user_id = patient.get("user_id")
        if not user_id:
            return

        state_messages = {
            "triaged": "Your symptoms have been assessed. You'll be assigned to a doctor shortly.",
            "queued": "You've been added to the doctor's queue. Please wait for your turn.",
            "in_consultation": "The doctor is ready to see you now!",
            "investigation_ordered": "Your doctor has ordered some tests. Please proceed to the lab.",
            "investigation_complete": "Your test results are ready. The doctor will review them.",
            "prescribed": "Your prescription is ready and has been sent to the pharmacy.",
            "at_pharmacy": "Your medicines are being prepared at the pharmacy.",
            "dispensed": "Your medicines are ready for pickup!",
            "billing": "Please proceed to the billing counter.",
            "discharged": "Your visit is complete. Thank you for choosing MediFlow!",
        }

        message = state_messages.get(new_state, f"Your status has been updated to: {new_state}")
        if notes:
            message += f"\n\nNote: {notes}"

        db.create_notification({
            "user_id": user_id,
            "type": "workflow_update",
            "title": f"Status Update: {_state_label(new_state)}",
            "message": message,
        })

    except Exception as e:
        logger.warning(f"Failed to send patient notification: {e}")
