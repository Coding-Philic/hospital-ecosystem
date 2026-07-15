"""
MediFlow AI — Notification Agent
==================================
Handles creating and dispatching notifications to users.
Supports in-app notifications with extensible hooks for
SMS/WhatsApp/Push notifications in future.
"""

import logging
from typing import Optional
from database import queries as db

logger = logging.getLogger(__name__)


def notify_user(
    user_id: str,
    notification_type: str,
    title: str,
    message: str,
    action_url: str = "",
    metadata: Optional[dict] = None,
) -> dict:
    """
    Send a notification to a user.

    Args:
        user_id: Target user's ID
        notification_type: Type of notification (queue_update, prescription_ready, etc.)
        title: Notification title
        message: Notification body
        action_url: Optional action URL
        metadata: Optional metadata dict

    Returns:
        dict with success status
    """
    try:
        data = {
            "user_id": user_id,
            "type": notification_type,
            "title": title,
            "message": message,
            "action_url": action_url,
            "metadata": metadata or {},
        }
        db.create_notification(data)
        logger.info(f"Notification sent to {user_id}: {title}")
        return {"success": True, "message": "Notification sent."}

    except Exception as e:
        logger.error(f"Failed to send notification: {e}")
        return {"success": False, "message": f"Error: {str(e)}"}


def notify_queue_update(
    patient_user_id: str,
    token_number: str,
    queue_position: int,
    estimated_wait: str,
    doctor_name: str,
) -> dict:
    """Send a queue position update notification."""
    return notify_user(
        user_id=patient_user_id,
        notification_type="queue_update",
        title=f"Queue Update — Token {token_number}",
        message=(
            f"Your position: #{queue_position}\n"
            f"Estimated wait: {estimated_wait}\n"
            f"Doctor: {doctor_name}"
        ),
        metadata={
            "token_number": token_number,
            "queue_position": queue_position,
            "estimated_wait": estimated_wait,
        },
    )


def notify_consultation_ready(patient_user_id: str, doctor_name: str, room: str = "") -> dict:
    """Notify patient that their consultation is about to begin."""
    msg = f"Dr. {doctor_name} is ready to see you!"
    if room:
        msg += f"\nPlease proceed to {room}."
    return notify_user(
        user_id=patient_user_id,
        notification_type="consultation_ready",
        title="Your Turn!",
        message=msg,
    )


def notify_prescription_ready(patient_user_id: str, prescription_code: str) -> dict:
    """Notify patient that their prescription has been created."""
    return notify_user(
        user_id=patient_user_id,
        notification_type="prescription_ready",
        title="Prescription Ready",
        message=f"Your prescription ({prescription_code}) has been created and sent to the pharmacy.",
        metadata={"prescription_code": prescription_code},
    )


def notify_pharmacy_ready(patient_user_id: str, prescription_code: str) -> dict:
    """Notify patient that their medicines are ready for pickup."""
    return notify_user(
        user_id=patient_user_id,
        notification_type="pharmacy_ready",
        title="Medicines Ready!",
        message=f"Your medicines for prescription {prescription_code} are ready for pickup at the pharmacy.",
        metadata={"prescription_code": prescription_code},
    )


def notify_all_pharmacists(title: str, message: str, metadata: Optional[dict] = None) -> dict:
    """Send a notification to all pharmacists."""
    try:
        pharmacists = db.get_users_by_role("pharmacist")
        for pharmacist in pharmacists:
            notify_user(
                user_id=pharmacist["id"],
                notification_type="prescription_ready",
                title=title,
                message=message,
                metadata=metadata,
            )
        return {"success": True, "message": f"Notified {len(pharmacists)} pharmacists."}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def notify_receptionist(title: str, message: str, metadata: Optional[dict] = None) -> dict:
    """Send a notification to all receptionists."""
    try:
        receptionists = db.get_users_by_role("receptionist")
        for receptionist in receptionists:
            notify_user(
                user_id=receptionist["id"],
                notification_type="system_alert",
                title=title,
                message=message,
                metadata=metadata,
            )
        return {"success": True, "message": f"Notified {len(receptionists)} receptionists."}
    except Exception as e:
        return {"success": False, "message": f"Error: {str(e)}"}


def get_user_notifications(user_id: str, unread_only: bool = False) -> list:
    """Get notifications for a user."""
    return db.get_notifications(user_id, unread_only)


def mark_read(notification_id: str) -> dict:
    """Mark a single notification as read."""
    db.mark_notification_read(notification_id)
    return {"success": True}


def mark_all_read(user_id: str) -> dict:
    """Mark all notifications as read for a user."""
    db.mark_all_notifications_read(user_id)
    return {"success": True}
