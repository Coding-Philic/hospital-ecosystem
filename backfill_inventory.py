import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import queries as db
from database.supabase_client import get_supabase_admin_client

client = get_supabase_admin_client()

# Fetch all medicines
med_res = client.table("medicines").select("*").execute()
medicines = getattr(med_res, "data", [])

# Fetch all inventory
inv_res = client.table("pharmacy_inventory").select("*").execute()
inventory = getattr(inv_res, "data", [])
inventory_med_ids = {inv["medicine_id"] for inv in inventory}

# Find orphaned medicines
missing = []
for m in medicines:
    if m["id"] not in inventory_med_ids:
        missing.append({
            "medicine_id": m["id"],
            "quantity_available": 0,
            "reorder_level": 10,
            "selling_price": m.get("unit_price", 10.0),
            "batch_number": "BATCH-BACKFILL",
            "expiry_date": "2027-12-31"
        })

print(f"Found {len(missing)} medicines missing inventory records.")
if missing:
    client.table("pharmacy_inventory").insert(missing).execute()
    print("Successfully backfilled.")
