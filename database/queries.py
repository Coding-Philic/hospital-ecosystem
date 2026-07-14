"""
MediFlow AI — Database CRUD Operations
========================================
All database queries centralized here for maintainability.
Uses Supabase Python client for PostgreSQL operations.
"""

from datetime import datetime, date
from typing import List, Optional
from database.supabase_client import get_supabase_client, get_supabase_admin_client


# ╔══════════════════════════════════════════════════════════╗
# ║  DEPARTMENT QUERIES                                       ║
# ╚══════════════════════════════════════════════════════════╝

def get_all_departments() -> list:
    """Fetch all active departments."""
    client = get_supabase_admin_client()
    response = client.table("departments").select("*").eq("is_active", True).order("name").execute()
    return getattr(response, "data", []) if response else []


def get_department_by_name(name: str) -> dict:
    """Fetch a department by name."""
    client = get_supabase_admin_client()
    response = client.table("departments").select("*").eq("name", name).maybe_single().execute()
    return getattr(response, "data", None) if response else None


def get_department_by_id(department_id: str) -> dict:
    """Fetch a department by ID."""
    client = get_supabase_admin_client()
    response = client.table("departments").select("*").eq("id", department_id).maybe_single().execute()
    return getattr(response, "data", None) if response else None


# ╔══════════════════════════════════════════════════════════╗
# ║  USER QUERIES                                             ║
# ╚══════════════════════════════════════════════════════════╝

def get_user_profile(user_id: str) -> dict:
    """Fetch a user profile by ID."""
    client = get_supabase_admin_client()
    response = client.table("users").select("*").eq("id", user_id).maybe_single().execute()
    return getattr(response, "data", None) if response else None


def get_users_by_role(role: str) -> list:
    """Fetch all users with a specific role."""
    client = get_supabase_admin_client()
    response = client.table("users").select("*").eq("role", role).eq("is_active", True).order("full_name").execute()
    return getattr(response, "data", []) if response else []


def update_user_profile(user_id: str, data: dict) -> dict:
    """Update a user's profile."""
    client = get_supabase_admin_client()
    response = client.table("users").update(data).eq("id", user_id).execute()
    return getattr(response, "data", None) if response else None


def get_all_users() -> list:
    """Fetch all users (admin only)."""
    client = get_supabase_admin_client()
    response = client.table("users").select("*").order("created_at", desc=True).execute()
    return getattr(response, "data", []) if response else []


# ╔══════════════════════════════════════════════════════════╗
# ║  DOCTOR QUERIES                                           ║
# ╚══════════════════════════════════════════════════════════╝

def get_all_doctors() -> list:
    """Fetch all doctors with their user and department info."""
    client = get_supabase_admin_client()
    response = client.table("doctors").select(
        "*, users!doctors_user_id_fkey(full_name, email, phone), departments!doctors_department_id_fkey(name)"
    ).order("created_at").execute()
    return getattr(response, "data", []) if response else []


def get_available_doctors(department_id: str = None) -> list:
    """Fetch doctors who are currently available, optionally filtered by department."""
    client = get_supabase_admin_client()
    query = client.table("doctors").select(
        "*, users!doctors_user_id_fkey(full_name, email), departments!doctors_department_id_fkey(name)"
    ).eq("status", "available")

    if department_id:
        query = query.eq("department_id", department_id)

    response = query.execute()
    return getattr(response, "data", []) if response else []


def get_doctor_by_user_id(user_id: str) -> dict:
    """Fetch a doctor profile by their user ID."""
    client = get_supabase_admin_client()
    response = client.table("doctors").select(
        "*, users!doctors_user_id_fkey(full_name, email), departments!doctors_department_id_fkey(name)"
    ).eq("user_id", user_id).maybe_single().execute()
    return getattr(response, "data", None) if response else None


def update_doctor_status(doctor_id: str, status: str) -> dict:
    """Update a doctor's availability status."""
    client = get_supabase_admin_client()
    response = client.table("doctors").update({"status": status}).eq("id", doctor_id).execute()
    return getattr(response, "data", None) if response else None


def create_doctor(data: dict) -> dict:
    """Create a new doctor record."""
    client = get_supabase_admin_client()
    response = client.table("doctors").insert(data).execute()
    return getattr(response, "data", None) if response else None


def increment_doctor_token(doctor_id: str) -> int:
    """
    Atomically increment the current token number for a doctor and return new value.
    Uses a PostgreSQL function (RPC) to ensure atomicity — prevents duplicate tokens
    when multiple patients submit at the same time.
    """
    client = get_supabase_admin_client()
    try:
        # Atomic increment via Supabase RPC (PostgreSQL function)
        result = client.rpc("increment_and_return_token", {"p_doctor_id": doctor_id}).execute()
        if result.data is not None:
            return result.data
    except Exception:
        pass  # RPC not deployed yet — fall through to non-atomic fallback

    # Fallback: read-then-write (less safe but functional)
    doc = client.table("doctors").select("current_token").eq("id", doctor_id).maybe_single().execute()
    new_token = (doc.data.get("current_token", 0) or 0) + 1
    client.table("doctors").update({"current_token": new_token}).eq("id", doctor_id).execute()
    return new_token


# ╔══════════════════════════════════════════════════════════╗
# ║  PATIENT QUERIES                                          ║
# ╚══════════════════════════════════════════════════════════╝

def get_patient_by_user_id(user_id: str) -> dict:
    """Fetch a patient profile by their user ID."""
    client = get_supabase_admin_client()
    response = client.table("patients").select(
        "*, users!patients_user_id_fkey(full_name, email, phone)"
    ).eq("user_id", user_id).maybe_single().execute()
    return getattr(response, "data", None) if response else None


def create_patient(data: dict) -> dict:
    """Create a new patient record."""
    client = get_supabase_admin_client()
    response = client.table("patients").insert(data).execute()
    return getattr(response, "data", None) if response else None


def update_patient(patient_id: str, data: dict) -> dict:
    """Update a patient record."""
    client = get_supabase_admin_client()
    response = client.table("patients").update(data).eq("id", patient_id).execute()
    return getattr(response, "data", None) if response else None


def get_all_patients() -> list:
    """Fetch all patients with user info."""
    client = get_supabase_admin_client()
    response = client.table("patients").select(
        "*, users!patients_user_id_fkey(full_name, email, phone)"
    ).order("created_at", desc=True).execute()
    return getattr(response, "data", []) if response else []


def search_patients(search_term: str) -> list:
    """Search patients by name or patient ID code."""
    client = get_supabase_admin_client()
    response = client.table("patients").select(
        "*, users!patients_user_id_fkey(full_name, email, phone)"
    ).or_(f"patient_id_code.ilike.%{search_term}%").execute()
    return getattr(response, "data", []) if response else []


# ╔══════════════════════════════════════════════════════════╗
# ║  APPOINTMENT / QUEUE QUERIES                              ║
# ╚══════════════════════════════════════════════════════════╝

def create_appointment(data: dict) -> dict:
    """Create a new appointment/queue token."""
    client = get_supabase_admin_client()
    response = client.table("appointments").insert(data).execute()
    return getattr(response, "data", None) if response else None


def get_appointments_by_patient(patient_id: str, status: str = None) -> list:
    """Fetch appointments for a patient, optionally filtered by status."""
    client = get_supabase_admin_client()
    query = client.table("appointments").select(
        "*, doctors!appointments_doctor_id_fkey(*, users!doctors_user_id_fkey(full_name)), departments!appointments_department_id_fkey(name)"
    ).eq("patient_id", patient_id).order("created_at", desc=True)

    if status:
        query = query.eq("status", status)

    response = query.execute()
    return getattr(response, "data", []) if response else []


def get_appointments_by_doctor(doctor_id: str, date_filter: str = None, status: str = None) -> list:
    """Fetch appointments for a doctor, optionally filtered by date and status."""
    client = get_supabase_admin_client()
    query = client.table("appointments").select(
        "*, patients!appointments_patient_id_fkey(*, users!patients_user_id_fkey(full_name, phone)), departments!appointments_department_id_fkey(name)"
    ).eq("doctor_id", doctor_id).order("queue_position")

    if date_filter:
        query = query.eq("scheduled_date", date_filter)
    if status:
        query = query.eq("status", status)

    response = query.execute()
    return getattr(response, "data", []) if response else []


def get_today_appointments(department_id: str = None) -> list:
    """Fetch all appointments for today, optionally filtered by department."""
    client = get_supabase_admin_client()
    today = date.today().isoformat()
    query = client.table("appointments").select(
        "*, patients!appointments_patient_id_fkey(patient_id_code, users!patients_user_id_fkey(full_name)), "
        "doctors!appointments_doctor_id_fkey(users!doctors_user_id_fkey(full_name)), "
        "departments!appointments_department_id_fkey(name)"
    ).eq("scheduled_date", today).order("queue_position")

    if department_id:
        query = query.eq("department_id", department_id)

    response = query.execute()
    return getattr(response, "data", []) if response else []


def update_appointment(appointment_id: str, data: dict) -> dict:
    """Update an appointment record."""
    client = get_supabase_admin_client()
    response = client.table("appointments").update(data).eq("id", appointment_id).execute()
    return getattr(response, "data", None) if response else None


def get_queue_position(doctor_id: str) -> int:
    """Get the current queue size for a doctor (today's waiting appointments)."""
    client = get_supabase_admin_client()
    today = date.today().isoformat()
    response = client.table("appointments").select("id", count="exact").eq(
        "doctor_id", doctor_id
    ).eq("scheduled_date", today).eq("status", "waiting").execute()
    return response.count or 0


def get_appointment_by_id(appointment_id: str) -> dict:
    """Fetch a single appointment by ID."""
    client = get_supabase_admin_client()
    response = client.table("appointments").select(
        "*, patients!appointments_patient_id_fkey(*, users!patients_user_id_fkey(full_name, phone)), "
        "doctors!appointments_doctor_id_fkey(*, users!doctors_user_id_fkey(full_name)), "
        "departments!appointments_department_id_fkey(name)"
    ).eq("id", appointment_id).maybe_single().execute()
    return getattr(response, "data", None) if response else None


# ╔══════════════════════════════════════════════════════════╗
# ║  CONSULTATION QUERIES                                     ║
# ╚══════════════════════════════════════════════════════════╝

def create_consultation(data: dict) -> dict:
    """Create a new consultation record."""
    client = get_supabase_admin_client()
    response = client.table("consultations").insert(data).execute()
    return getattr(response, "data", None) if response else None


def get_consultation_by_appointment(appointment_id: str) -> dict:
    """Fetch consultation for a specific appointment."""
    client = get_supabase_admin_client()
    response = client.table("consultations").select("*").eq("appointment_id", appointment_id).maybe_single().execute()
    return getattr(response, "data", None) if response else None


def get_consultations_by_patient(patient_id: str) -> list:
    """Fetch all consultations for a patient."""
    client = get_supabase_admin_client()
    response = client.table("consultations").select(
        "*, doctors!consultations_doctor_id_fkey(users!doctors_user_id_fkey(full_name))"
    ).eq("patient_id", patient_id).order("created_at", desc=True).execute()
    return getattr(response, "data", []) if response else []


def update_consultation(consultation_id: str, data: dict) -> dict:
    """Update a consultation record."""
    client = get_supabase_admin_client()
    response = client.table("consultations").update(data).eq("id", consultation_id).execute()
    return getattr(response, "data", None) if response else None


# ╔══════════════════════════════════════════════════════════╗
# ║  MEDICINE QUERIES                                         ║
# ╚══════════════════════════════════════════════════════════╝

def get_all_medicines() -> list:
    """Fetch all active medicines."""
    client = get_supabase_admin_client()
    response = client.table("medicines").select("*").eq("is_active", True).order("name").execute()
    return getattr(response, "data", []) if response else []


def search_medicines(search_term: str) -> list:
    """Search medicines by name or generic name."""
    client = get_supabase_admin_client()
    response = client.table("medicines").select("*").or_(
        f"name.ilike.%{search_term}%,generic_name.ilike.%{search_term}%"
    ).eq("is_active", True).execute()
    return getattr(response, "data", []) if response else []


def get_medicine_by_id(medicine_id: str) -> dict:
    """Fetch a single medicine by ID."""
    client = get_supabase_admin_client()
    response = client.table("medicines").select("*").eq("id", medicine_id).maybe_single().execute()
    return getattr(response, "data", None) if response else None


def create_medicine(data: dict) -> dict:
    """Add a new medicine to the catalog."""
    client = get_supabase_admin_client()
    response = client.table("medicines").insert(data).execute()
    return getattr(response, "data", None) if response else None


# ╔══════════════════════════════════════════════════════════╗
# ║  PRESCRIPTION QUERIES                                     ║
# ╚══════════════════════════════════════════════════════════╝

def create_prescription(data: dict) -> dict:
    """Create a new prescription."""
    client = get_supabase_admin_client()
    response = client.table("prescriptions").insert(data).execute()
    return getattr(response, "data", None) if response else None


def create_prescription_items(items: list) -> list:
    """Bulk insert prescription items."""
    client = get_supabase_admin_client()
    response = client.table("prescription_items").insert(items).execute()
    return getattr(response, "data", []) if response else []


def get_prescriptions_by_patient(patient_id: str) -> list:
    """Fetch all prescriptions for a patient."""
    client = get_supabase_admin_client()
    response = client.table("prescriptions").select(
        "*, doctors!prescriptions_doctor_id_fkey(users!doctors_user_id_fkey(full_name)), "
        "prescription_items(*)"
    ).eq("patient_id", patient_id).order("created_at", desc=True).execute()
    return getattr(response, "data", []) if response else []


def get_pending_prescriptions() -> list:
    """Fetch all prescriptions pending pharmacy processing."""
    client = get_supabase_admin_client()
    response = client.table("prescriptions").select(
        "*, patients!prescriptions_patient_id_fkey(patient_id_code, users!patients_user_id_fkey(full_name, phone)), "
        "doctors!prescriptions_doctor_id_fkey(users!doctors_user_id_fkey(full_name)), "
        "prescription_items(*)"
    ).in_("status", ["created", "sent_to_pharmacy", "partially_available"]).order("created_at").execute()
    return getattr(response, "data", []) if response else []


def update_prescription(prescription_id: str, data: dict) -> dict:
    """Update a prescription's status or details."""
    client = get_supabase_admin_client()
    response = client.table("prescriptions").update(data).eq("id", prescription_id).execute()
    return getattr(response, "data", None) if response else None


def update_prescription_item(item_id: str, data: dict) -> dict:
    """Update a prescription item (e.g., mark in-stock, approve substitute)."""
    client = get_supabase_admin_client()
    response = client.table("prescription_items").update(data).eq("id", item_id).execute()
    return getattr(response, "data", None) if response else None


# ╔══════════════════════════════════════════════════════════╗
# ║  PHARMACY INVENTORY QUERIES                               ║
# ╚══════════════════════════════════════════════════════════╝

def get_pharmacy_inventory() -> list:
    """Fetch all pharmacy inventory with medicine details."""
    client = get_supabase_admin_client()
    response = client.table("pharmacy_inventory").select(
        "*, medicines!pharmacy_inventory_medicine_id_fkey(*)"
    ).order("updated_at", desc=True).execute()
    return getattr(response, "data", []) if response else []


def check_medicine_stock(medicine_id: str) -> dict:
    """Check stock availability for a specific medicine."""
    client = get_supabase_admin_client()
    response = client.table("pharmacy_inventory").select(
        "*, medicines!pharmacy_inventory_medicine_id_fkey(name, generic_name, alternative_medicine_ids)"
    ).eq("medicine_id", medicine_id).maybe_single().execute()
    return getattr(response, "data", None) if response else None


def update_inventory(inventory_id: str, data: dict) -> dict:
    """Update inventory quantities."""
    client = get_supabase_admin_client()
    response = client.table("pharmacy_inventory").update(data).eq("id", inventory_id).execute()
    return getattr(response, "data", None) if response else None


def get_low_stock_items(threshold: int = 10) -> list:
    """Fetch items below reorder level."""
    client = get_supabase_admin_client()
    response = client.table("pharmacy_inventory").select(
        "*, medicines!pharmacy_inventory_medicine_id_fkey(name, generic_name)"
    ).lte("quantity_available", threshold).execute()
    return getattr(response, "data", []) if response else []


def get_medicine_alternatives(medicine_id: str) -> list:
    """Get alternative medicines for a given medicine."""
    client = get_supabase_admin_client()
    # Get the medicine with its alternatives
    medicine = get_medicine_by_id(medicine_id)
    if not medicine or not medicine.get("alternative_medicine_ids"):
        # Try to find medicines with same generic name
        if medicine and medicine.get("generic_name"):
            response = client.table("medicines").select("*").eq(
                "generic_name", medicine["generic_name"]
            ).neq("id", medicine_id).eq("is_active", True).execute()
            return getattr(response, "data", []) if response else []
        return []

    alt_ids = medicine["alternative_medicine_ids"]
    response = client.table("medicines").select("*").in_("id", alt_ids).execute()
    return getattr(response, "data", []) if response else []


# ╔══════════════════════════════════════════════════════════╗
# ║  WORKFLOW STATE QUERIES                                    ║
# ╚══════════════════════════════════════════════════════════╝

def create_workflow_state(data: dict) -> dict:
    """Insert a new workflow state transition."""
    client = get_supabase_admin_client()
    response = client.table("workflow_states").insert(data).execute()
    return getattr(response, "data", None) if response else None


def get_workflow_history(appointment_id: str) -> list:
    """Fetch the complete workflow history for an appointment."""
    client = get_supabase_admin_client()
    response = client.table("workflow_states").select(
        "*, users!workflow_states_transitioned_by_fkey(full_name)"
    ).eq("appointment_id", appointment_id).order("created_at").execute()
    return getattr(response, "data", []) if response else []


def get_current_workflow_state(appointment_id: str) -> dict:
    """Get the latest/current workflow state for an appointment."""
    client = get_supabase_admin_client()
    response = client.table("workflow_states").select("*").eq(
        "appointment_id", appointment_id
    ).order("created_at", desc=True).limit(1).maybe_single().execute()
    return getattr(response, "data", None) if response else None


def get_patients_by_workflow_state(state: str) -> list:
    """Get all patients currently in a specific workflow state (today)."""
    client = get_supabase_admin_client()
    today = date.today().isoformat()
    # Get latest workflow state for each appointment today
    response = client.table("workflow_states").select(
        "*, appointments!workflow_states_appointment_id_fkey(scheduled_date, token_number, "
        "patients!appointments_patient_id_fkey(patient_id_code, users!patients_user_id_fkey(full_name)))"
    ).eq("current_state", state).order("created_at", desc=True).execute()
    return getattr(response, "data", []) if response else []


# ╔══════════════════════════════════════════════════════════╗
# ║  AUDIT LOG QUERIES                                        ║
# ╚══════════════════════════════════════════════════════════╝

def create_audit_entry(data: dict) -> dict:
    """Insert a new audit log entry."""
    client = get_supabase_admin_client()
    response = client.table("audit_log").insert(data).execute()
    return getattr(response, "data", None) if response else None


def get_audit_log(limit: int = 100, entity_type: str = None) -> list:
    """Fetch audit log entries."""
    client = get_supabase_admin_client()
    query = client.table("audit_log").select(
        "*, users!audit_log_actor_id_fkey(full_name)"
    ).order("created_at", desc=True).limit(limit)

    if entity_type:
        query = query.eq("entity_type", entity_type)

    response = query.execute()
    return getattr(response, "data", []) if response else []


# ╔══════════════════════════════════════════════════════════╗
# ║  NOTIFICATION QUERIES                                     ║
# ╚══════════════════════════════════════════════════════════╝

def create_notification(data: dict) -> dict:
    """Create a new notification."""
    client = get_supabase_admin_client()
    response = client.table("notifications").insert(data).execute()
    return getattr(response, "data", None) if response else None


def get_notifications(user_id: str, unread_only: bool = False) -> list:
    """Fetch notifications for a user."""
    client = get_supabase_admin_client()
    query = client.table("notifications").select("*").eq("user_id", user_id).order("created_at", desc=True).limit(50)

    if unread_only:
        query = query.eq("is_read", False)

    response = query.execute()
    return getattr(response, "data", []) if response else []


def mark_notification_read(notification_id: str) -> dict:
    """Mark a notification as read."""
    client = get_supabase_admin_client()
    response = client.table("notifications").update({"is_read": True}).eq("id", notification_id).execute()
    return getattr(response, "data", None) if response else None


def mark_all_notifications_read(user_id: str) -> dict:
    """Mark all notifications as read for a user."""
    client = get_supabase_admin_client()
    response = client.table("notifications").update({"is_read": True}).eq("user_id", user_id).eq("is_read", False).execute()
    return getattr(response, "data", None) if response else None


def get_unread_count(user_id: str) -> int:
    """Get unread notification count for a user."""
    client = get_supabase_admin_client()
    response = client.table("notifications").select("id", count="exact").eq("user_id", user_id).eq("is_read", False).execute()
    return response.count or 0


# ╔══════════════════════════════════════════════════════════╗
# ║  ANALYTICS / STATS QUERIES                                ║
# ╚══════════════════════════════════════════════════════════╝

def get_today_stats() -> dict:
    """Get today's summary statistics for admin dashboard."""
    client = get_supabase_admin_client()
    today = date.today().isoformat()

    # Total appointments today
    appts = client.table("appointments").select("id", count="exact").eq("scheduled_date", today).execute()
    total_appointments = appts.count or 0

    # Waiting patients
    waiting = client.table("appointments").select("id", count="exact").eq("scheduled_date", today).eq("status", "waiting").execute()
    waiting_count = waiting.count or 0

    # Completed consultations
    completed = client.table("appointments").select("id", count="exact").eq("scheduled_date", today).eq("status", "completed").execute()
    completed_count = completed.count or 0

    # Active doctors
    active_docs = client.table("doctors").select("id", count="exact").eq("status", "available").execute()
    active_doctors = active_docs.count or 0

    # Pending prescriptions
    pending_rx = client.table("prescriptions").select("id", count="exact").in_("status", ["created", "sent_to_pharmacy"]).execute()
    pending_prescriptions = pending_rx.count or 0

    # Low stock count
    low_stock = get_low_stock_items()
    low_stock_count = len(low_stock)

    return {
        "total_appointments": total_appointments,
        "waiting_patients": waiting_count,
        "completed_consultations": completed_count,
        "active_doctors": active_doctors,
        "pending_prescriptions": pending_prescriptions,
        "low_stock_items": low_stock_count,
        "in_progress": total_appointments - waiting_count - completed_count,
    }
