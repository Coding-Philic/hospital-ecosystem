import sys
import os
from unittest.mock import MagicMock
sys.modules['streamlit'] = MagicMock()

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client
from config import config
client = create_client(config.SUPABASE_URL, os.environ.get("SUPABASE_SERVICE_ROLE_KEY"))
import database.queries
database.queries.get_supabase_admin_client = lambda: client

from agents.workflow_agent import transition_state

res = client.table("appointments").select("*").order("created_at", desc=True).limit(1).execute()
if res.data:
    appt = res.data[0]
    print(f"Token: {appt['token_number']}")
    print(f"Appointment ID: {appt['id']}")
    print(f"Patient ID: {appt['patient_id']}")
    
    res_doc = client.table("doctors").select("user_id").eq("id", appt["doctor_id"]).execute()
    doctor_user_id = res_doc.data[0]["user_id"] if res_doc.data else None
    
    result = transition_state(
        appt["id"], appt["patient_id"],
        "in_consultation", doctor_user_id, "doctor",
        "Consultation started"
    )
    print("Transition result:", result)
else:
    print("No appt found")
