"""
MediFlow AI — Centralized Configuration
========================================
Loads environment variables and provides app-wide configuration constants.
Supports model fallback chain for when Groq rate limits are reached.
"""

import os
from dotenv import load_dotenv

# Load .env file with override=True so changes take effect immediately without restarting the server
load_dotenv(override=True)


class Config:
    """Application configuration loaded from environment variables."""

    # ── Groq API ──────────────────────────────────────────────
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")

    # Model fallback chain — if primary model hits rate limit,
    # the system automatically tries the next model in the chain.
    # Update these in .env to switch models easily.
    PRIMARY_MODEL: str = os.environ.get("PRIMARY_MODEL", "openai/gpt-oss-120b")
    FALLBACK_MODEL_1: str = os.environ.get("FALLBACK_MODEL_1", "llama-3.3-70b-versatile")
    FALLBACK_MODEL_2: str = os.environ.get("FALLBACK_MODEL_2", "llama-3.1-8b-instant")

    MODEL_CHAIN: list = [PRIMARY_MODEL, FALLBACK_MODEL_1, FALLBACK_MODEL_2]

    # ── Supabase ──────────────────────────────────────────────
    SUPABASE_URL: str = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.environ.get("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY: str = os.environ.get("SUPABASE_SERVICE_KEY", "")

    # ── Application ───────────────────────────────────────────
    APP_NAME: str = os.environ.get("APP_NAME", "MediFlow AI")
    APP_VERSION: str = os.environ.get("APP_VERSION", "1.0.0")
    DEBUG: bool = os.environ.get("DEBUG", "False").lower() == "true"

    # ── Hospital Departments ──────────────────────────────────
    DEPARTMENTS: list = [
        "General Medicine",
        "Cardiology",
        "Dermatology",
        "Orthopedics",
        "Pediatrics",
        "ENT (Ear, Nose, Throat)",
        "Ophthalmology",
        "Gynecology",
        "Neurology",
        "Psychiatry",
        "Pulmonology",
        "Gastroenterology",
        "Urology",
        "Dental",
        "Emergency",
    ]

    # ── Urgency Levels ────────────────────────────────────────
    URGENCY_LEVELS: dict = {
        "routine": {"label": "Routine", "color": "#22c55e", "priority": 1},
        "semi_urgent": {"label": "Semi-Urgent", "color": "#f59e0b", "priority": 2},
        "urgent": {"label": "Urgent", "color": "#ef4444", "priority": 3},
        "emergency": {"label": "Emergency", "color": "#dc2626", "priority": 4},
    }

    # ── Workflow States ───────────────────────────────────────
    WORKFLOW_STATES: list = [
        "registered",
        "triaged",
        "queued",
        "in_consultation",
        "investigation_ordered",
        "investigation_complete",
        "prescribed",
        "at_pharmacy",
        "dispensed",
        "billing",
        "discharged",
    ]

    # ── Red-Flag Symptoms (bypass queue → emergency) ──────────
    RED_FLAG_SYMPTOMS: list = [
        "chest pain",
        "difficulty breathing",
        "shortness of breath",
        "stroke symptoms",
        "severe bleeding",
        "loss of consciousness",
        "seizure",
        "severe allergic reaction",
        "anaphylaxis",
        "heart attack",
        "severe head injury",
        "poisoning",
        "severe burn",
        "suicidal thoughts",
    ]

    # ── User Roles ────────────────────────────────────────────
    USER_ROLES: list = ["patient", "doctor", "receptionist", "pharmacist", "admin"]

    # ── Appointment Settings ──────────────────────────────────
    SLOT_DURATION_MINUTES: int = 15
    MAX_QUEUE_SIZE: int = 50
    WORKING_HOURS_START: int = 8   # 8 AM
    WORKING_HOURS_END: int = 20    # 8 PM


# Singleton instance
config = Config()
