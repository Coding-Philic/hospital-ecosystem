"""
MediFlow AI — Application Constants
====================================
Static constants used across the application.
"""

# ── Medicine Dosage Frequencies ───────────────────────────────
DOSAGE_FREQUENCIES = [
    "Once daily (OD)",
    "Twice daily (BD)",
    "Three times daily (TDS)",
    "Four times daily (QDS)",
    "Every 4 hours",
    "Every 6 hours",
    "Every 8 hours",
    "Every 12 hours",
    "As needed (SOS/PRN)",
    "Before meals (AC)",
    "After meals (PC)",
    "At bedtime (HS)",
    "Once weekly",
    "Stat (immediately)",
]

# ── Medicine Routes ───────────────────────────────────────────
MEDICINE_ROUTES = [
    "Oral",
    "Topical",
    "Intravenous (IV)",
    "Intramuscular (IM)",
    "Subcutaneous (SC)",
    "Inhalation",
    "Sublingual",
    "Rectal",
    "Ophthalmic (Eye)",
    "Otic (Ear)",
    "Nasal",
]

# ── Medicine Duration Units ───────────────────────────────────
DURATION_UNITS = ["days", "weeks", "months"]

# ── Investigation Types ───────────────────────────────────────
INVESTIGATION_TYPES = [
    "Complete Blood Count (CBC)",
    "Blood Sugar (Fasting/PP)",
    "Liver Function Test (LFT)",
    "Kidney Function Test (KFT)",
    "Lipid Profile",
    "Thyroid Profile (T3/T4/TSH)",
    "Urine Routine",
    "Chest X-Ray",
    "ECG",
    "Echocardiography",
    "Ultrasound",
    "CT Scan",
    "MRI",
    "Blood Culture",
    "Stool Test",
    "HbA1c",
    "Vitamin D",
    "Vitamin B12",
    "Iron Studies",
    "COVID-19 Test",
]

# ── Blood Groups ──────────────────────────────────────────────
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-", "Unknown"]

# ── Gender Options ────────────────────────────────────────────
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]

# ── Insurance Providers (Sample) ──────────────────────────────
INSURANCE_PROVIDERS = [
    "None / Self-Pay",
    "Star Health Insurance",
    "ICICI Lombard",
    "HDFC ERGO",
    "Bajaj Allianz",
    "New India Assurance",
    "Max Bupa",
    "Care Health Insurance",
    "Niva Bupa",
    "Government Scheme (Ayushman Bharat)",
    "Other",
]

# ── Notification Types ────────────────────────────────────────
NOTIFICATION_TYPES = [
    "queue_update",
    "consultation_ready",
    "prescription_ready",
    "pharmacy_ready",
    "investigation_result",
    "appointment_reminder",
    "system_alert",
    "workflow_update",
]

# ── Dashboard Colors (Solid, Minimal Theme) ───────────────────
COLORS = {
    "primary": "#007B8A",       # Teal
    "secondary": "#005F6B",     # Dark Teal
    "accent": "#3A9AD9",        # Medium Blue
    "light": "#6BCBEB",         # Light Blue
    "lightest": "#A2DFF7",      # Lightest Blue
    "success": "#22c55e",       # Green (for success states)
    "warning": "#f59e0b",       # Amber (for warnings)
    "danger": "#ef4444",        # Red (for errors/emergencies)
    "info": "#6BCBEB",          # Light Blue
    "bg_dark": "#ffffff",       # White background
    "bg_card": "#f8fafc",       # Very light gray for cards
    "bg_elevated": "#f1f5f9",   # Slightly darker gray for elevated
    "text_primary": "#1e293b",  # Dark slate for text
    "text_secondary": "#64748b",# Muted text
    "border": "#e2e8f0",        # Light border
}

# ── Workflow State Display Config ─────────────────────────────
WORKFLOW_DISPLAY = {
    "registered": {"icon": "", "label": "Registered", "color": COLORS["text_secondary"]},
    "triaged": {"icon": "", "label": "Triaged", "color": COLORS["light"]},
    "queued": {"icon": "", "label": "In Queue", "color": COLORS["accent"]},
    "in_consultation": {"icon": "", "label": "With Doctor", "color": COLORS["primary"]},
    "investigation_ordered": {"icon": "", "label": "Investigation", "color": COLORS["light"]},
    "investigation_complete": {"icon": "", "label": "Results Ready", "color": COLORS["light"]},
    "prescribed": {"icon": "", "label": "Prescribed", "color": COLORS["accent"]},
    "at_pharmacy": {"icon": "", "label": "At Pharmacy", "color": COLORS["primary"]},
    "dispensed": {"icon": "", "label": "Medicine Dispensed", "color": COLORS["secondary"]},
    "billing": {"icon": "", "label": "Billing", "color": COLORS["text_secondary"]},
    "discharged": {"icon": "", "label": "Discharged", "color": COLORS["secondary"]},
}
