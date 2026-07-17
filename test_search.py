import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import queries as db

patients = db.search_patients("Adnan")
print("Search by name 'Adnan':", len(patients))
for p in patients:
    print(p)

patients = db.search_patients("MF-")
print("Search by code 'MF-':", len(patients))
for p in patients:
    print(p)
