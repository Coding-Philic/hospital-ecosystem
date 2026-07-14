"""
MediFlow AI — Pydantic Data Models
====================================
Validation schemas for all database entities and API inputs/outputs.
"""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field


# ── User Models ───────────────────────────────────────────────

class UserCreate(BaseModel):
    email: str
    full_name: str
    phone: Optional[str] = ""
    role: str = "patient"


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = ""
    role: str
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[str] = None


# ── Department Models ─────────────────────────────────────────

class Department(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    floor_number: Optional[int] = 1
    is_active: bool = True


# ── Doctor Models ─────────────────────────────────────────────

class DoctorCreate(BaseModel):
    user_id: str
    department_id: str
    specialization: Optional[str] = ""
    qualification: Optional[str] = ""
    experience_years: Optional[int] = 0
    license_number: Optional[str] = ""
    consultation_fee: Optional[float] = 0
    max_daily_patients: Optional[int] = 30


class DoctorProfile(BaseModel):
    id: str
    user_id: str
    department_id: str
    specialization: Optional[str] = ""
    qualification: Optional[str] = ""
    experience_years: Optional[int] = 0
    status: str = "offline"
    max_daily_patients: int = 30
    current_token: int = 0
    # Joined fields
    full_name: Optional[str] = ""
    department_name: Optional[str] = ""
    email: Optional[str] = ""


# ── Patient Models ────────────────────────────────────────────

class PatientCreate(BaseModel):
    user_id: str
    patient_id_code: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = ""
    emergency_contact_name: Optional[str] = ""
    emergency_contact_phone: Optional[str] = ""
    insurance_provider: Optional[str] = "None / Self-Pay"
    insurance_id: Optional[str] = ""
    allergies: Optional[List[str]] = []
    chronic_conditions: Optional[List[str]] = []


class PatientProfile(BaseModel):
    id: str
    user_id: str
    patient_id_code: str
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    blood_group: Optional[str] = None
    address: Optional[str] = ""
    allergies: Optional[List[str]] = []
    chronic_conditions: Optional[List[str]] = []
    insurance_provider: Optional[str] = ""
    full_name: Optional[str] = ""


# ── Appointment Models ────────────────────────────────────────

class AppointmentCreate(BaseModel):
    patient_id: str
    doctor_id: str
    department_id: str
    token_number: str
    queue_position: int
    urgency: str = "routine"
    symptom_summary: Optional[str] = ""
    ai_recommended_department: Optional[str] = ""
    ai_urgency_score: Optional[str] = ""
    ai_confidence: Optional[float] = 0
    scheduled_date: Optional[str] = None


class AppointmentView(BaseModel):
    id: str
    patient_id: str
    doctor_id: str
    department_id: str
    token_number: str
    queue_position: int
    status: str
    urgency: str
    symptom_summary: Optional[str] = ""
    scheduled_date: Optional[str] = None
    estimated_time: Optional[str] = None
    # Joined fields
    patient_name: Optional[str] = ""
    doctor_name: Optional[str] = ""
    department_name: Optional[str] = ""


# ── Consultation Models ───────────────────────────────────────

class ConsultationCreate(BaseModel):
    appointment_id: str
    patient_id: str
    doctor_id: str
    symptoms: Optional[str] = ""
    examination_notes: Optional[str] = ""
    diagnosis: Optional[str] = ""
    diagnosis_code: Optional[str] = ""
    additional_notes: Optional[str] = ""
    follow_up_date: Optional[str] = None
    follow_up_notes: Optional[str] = ""
    vitals: Optional[dict] = {}


# ── Prescription Models ───────────────────────────────────────

class PrescriptionItemCreate(BaseModel):
    medicine_name: str
    dosage: str
    frequency: str
    duration: str
    route: str = "Oral"
    quantity: int = 1
    instructions: Optional[str] = ""
    medicine_id: Optional[str] = None


class PrescriptionCreate(BaseModel):
    consultation_id: str
    patient_id: str
    doctor_id: str
    prescription_code: str
    items: List[PrescriptionItemCreate]


# ── Pharmacy Models ───────────────────────────────────────────

class InventoryUpdate(BaseModel):
    medicine_id: str
    quantity_available: int
    batch_number: Optional[str] = ""
    expiry_date: Optional[str] = None
    selling_price: Optional[float] = 0


class StockCheckResult(BaseModel):
    medicine_name: str
    is_in_stock: bool
    quantity_available: int
    alternatives: Optional[List[dict]] = []


# ── Workflow Models ───────────────────────────────────────────

class WorkflowTransition(BaseModel):
    appointment_id: str
    patient_id: str
    current_state: str
    previous_state: Optional[str] = None
    transitioned_by: Optional[str] = None
    transitioned_by_role: Optional[str] = None
    notes: Optional[str] = ""
    metadata: Optional[dict] = {}


# ── Symptom Classification (AI Output) ───────────────────────

class SymptomClassification(BaseModel):
    recommended_department: str
    urgency_level: str
    confidence_score: float = Field(ge=0, le=1)
    reasoning: str
    is_emergency: bool = False
    red_flags_detected: List[str] = []
    suggested_investigations: List[str] = []


# ── Notification Models ───────────────────────────────────────

class NotificationCreate(BaseModel):
    user_id: str
    type: str
    title: str
    message: str
    action_url: Optional[str] = ""
    metadata: Optional[dict] = {}
