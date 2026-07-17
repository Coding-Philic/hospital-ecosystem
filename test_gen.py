import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agents.symptom_classifier import generate_clinical_notes_from_triage

patient_info = {"users": None, "allergies": None, "chronic_conditions": None}
vitals = {}
triage_summary = "test summary"
notes = generate_clinical_notes_from_triage(triage_summary, vitals, patient_info)
print("Result:", notes)
