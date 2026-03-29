import pymongo
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "hwsms_db")

def initialize_database():
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    for col in ["users", "departments", "requests", "schedules", "swap_requests"]:
        db[col].drop()

    # Realistic Hospital Mockup
    users = [
        {"id": "A001", "name": "Admin1", "password": "admin", "role": "Admin", "email": "visvafelix2005@gmail.com"}
    ]
    
    departments = ["Cardiology", "Neurology", "Oncology", "Pediatrics"]
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    shifts = [1, 2, "Any"]
    
    # Generate 6 Doctors and 6 Nurses per department to guarantee CSP satisfies the 14 shifts per week requirement.
    doc_id_counter = 1
    nur_id_counter = 1
    
    for dept in departments:
        # 6 Doctors
        for i in range(6):
            users.append({
                "id": f"D{doc_id_counter:03d}",
                "name": f"Dr. {dept[:3]}Doc{i+1}",
                "password": "pass",
                "role": "Doctor",
                "department": dept,
                "experience": 5 + i,
                "email": "visvafelix2005@gmail.com",
                "Assigned": False,
                "preferred_off_day": days[i % 7],
                "preferred_shift": shifts[i % 3], 
                "max_shifts_per_week": 5 if i % 2 == 0 else 6
            })
            doc_id_counter += 1
            
        # 6 Nurses
        for i in range(6):
            users.append({
                "id": f"N{nur_id_counter:03d}",
                "name": f"Nurse {dept[:3]}Nur{i+1}",
                "password": "pass",
                "role": "Nurse",
                "department": dept,
                "experience": 2 + i,
                "email": "visvafelix2005@gmail.com",
                "Assigned": False,
                "preferred_off_day": days[(i+3) % 7],
                "preferred_shift": shifts[(i+1) % 3], 
                "max_shifts_per_week": 5
            })
            nur_id_counter += 1

    # Specifically re-add the user names you wanted mapped to ensure you can login
    users.extend([
        {"id": "D997", "name": "Dr. Visva", "password": "pass", "role": "Doctor", "department": "Cardiology", "experience": 10, "email": "visvafelix2005@gmail.com", "Assigned": False, "preferred_off_day": "Sunday", "preferred_shift": "Any", "max_shifts_per_week": 6},
        {"id": "D998", "name": "Dr. Ghiri", "password": "pass", "role": "Doctor", "department": "Neurology", "experience": 8, "email": "visvafelix2005@gmail.com", "Assigned": False, "preferred_off_day": "Saturday", "preferred_shift": 1, "max_shifts_per_week": 5},
        {"id": "D999", "name": "Dr. Dipankar", "password": "pass", "role": "Doctor", "department": "Oncology", "experience": 5, "email": "visvafelix2005@gmail.com", "Assigned": False, "preferred_off_day": "Wednesday", "preferred_shift": 2, "max_shifts_per_week": 5},
    ])

    db["users"].insert_many(users)
    print(f"Database seeded successfully with {len(users)} staff members providing massive coverage capacity.")

if __name__ == "__main__":
    print(f"Connecting to MongoDB at {MONGO_URI} -> {DB_NAME}")
    initialize_database()
