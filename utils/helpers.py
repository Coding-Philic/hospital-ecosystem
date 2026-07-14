"""
MediFlow AI — Utility Helper Functions
=======================================
Common utility functions used across the application.
"""

import hashlib
import random
import string
from datetime import datetime, timedelta
from typing import Optional


def generate_token_number(department: str, position: int) -> str:
    """
    Generate a queue token number.
    Format: DEPT_PREFIX-NUMBER (e.g., GEN-001, CARD-002)
    """
    dept_prefixes = {
        "General Medicine": "GEN",
        "Cardiology": "CARD",
        "Dermatology": "DERM",
        "Orthopedics": "ORTH",
        "Pediatrics": "PED",
        "ENT (Ear, Nose, Throat)": "ENT",
        "Ophthalmology": "OPH",
        "Gynecology": "GYN",
        "Neurology": "NEUR",
        "Psychiatry": "PSY",
        "Pulmonology": "PULM",
        "Gastroenterology": "GAST",
        "Urology": "URO",
        "Dental": "DENT",
        "Emergency": "EMRG",
    }
    prefix = dept_prefixes.get(department, "GEN")
    return f"{prefix}-{position:03d}"


def estimate_wait_time(queue_position: int, slot_duration_minutes: int = 15) -> dict:
    """
    Estimate wait time based on queue position.
    Returns dict with minutes and human-readable string.
    """
    total_minutes = queue_position * slot_duration_minutes
    hours = total_minutes // 60
    minutes = total_minutes % 60

    if hours > 0:
        human_readable = f"~{hours}h {minutes}m"
    else:
        human_readable = f"~{minutes} min"

    return {
        "total_minutes": total_minutes,
        "display": human_readable,
        "estimated_time": datetime.now() + timedelta(minutes=total_minutes),
    }


def generate_patient_id() -> str:
    """Generate a unique patient ID: MF-XXXXXXXX."""
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(random.choices(chars, k=8))
    return f"MF-{random_part}"


def generate_prescription_id() -> str:
    """Generate a unique prescription ID: RX-XXXXXXXXXX."""
    chars = string.ascii_uppercase + string.digits
    random_part = "".join(random.choices(chars, k=10))
    return f"RX-{random_part}"


def format_datetime(dt: Optional[datetime] = None, fmt: str = "%d %b %Y, %I:%M %p") -> str:
    """Format a datetime object to a human-readable string."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def format_date(dt: Optional[datetime] = None, fmt: str = "%d %b %Y") -> str:
    """Format a datetime object to a date-only string."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime(fmt)


def calculate_age(dob: datetime) -> int:
    """Calculate age from date of birth."""
    today = datetime.now()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


def urgency_badge_html(urgency: str) -> str:
    """Generate HTML badge for urgency level display in Streamlit."""
    colors = {
        "routine": ("#22c55e", "#052e16"),
        "semi_urgent": ("#f59e0b", "#451a03"),
        "urgent": ("#ef4444", "#450a0a"),
        "emergency": ("#dc2626", "#450a0a"),
    }
    bg_color, text_bg = colors.get(urgency, ("#94a3b8", "#1e293b"))
    label = urgency.replace("_", " ").title()
    return f'<span style="background:{bg_color};color:white;padding:2px 10px;border-radius:12px;font-size:0.8em;font-weight:600;">{label}</span>'


def workflow_state_badge(state: str) -> str:
    """Generate a styled badge for workflow state display."""
    from utils.constants import WORKFLOW_DISPLAY
    display = WORKFLOW_DISPLAY.get(state, {"icon": "❓", "label": state, "color": "#94a3b8"})
    return f'{display["icon"]} {display["label"]}'


def hash_password(password: str) -> str:
    """Hash a password using SHA-256 (for display/demo purposes — Supabase Auth handles real auth)."""
    return hashlib.sha256(password.encode()).hexdigest()


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to a maximum length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def get_greeting() -> str:
    """Return a time-appropriate greeting."""
    hour = datetime.now().hour
    if hour < 12:
        return "Good Morning"
    elif hour < 17:
        return "Good Afternoon"
    else:
        return "Good Evening"
