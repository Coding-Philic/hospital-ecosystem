import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import queries as db

inv = db.get_pharmacy_inventory()
if inv:
    print("Keys in inventory:")
    for k in inv[0].keys():
        print(f"  {k}: {inv[0][k]}")
