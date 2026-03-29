import pymongo
import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "hwsms_db")

client = pymongo.MongoClient(MONGO_URI)
db = client[DB_NAME]

def authenticate_user(name, password):
    return db["users"].find_one({"name": name, "password": password})

def get_all_users_by_role(role):
    return list(db["users"].find({"role": role}))

def get_colleagues(department, role):
    return list(db["users"].find({"department": department, "role": role}))

def get_departments():
    return db["users"].distinct("department", {"department": {"$ne": None}})

# --- Leave Management & Conflict Engine ---

def check_leave_conflict(user_id, request_date_str):
    """
    Checks if an employee is scheduled on the requested date, 
    and whether approving this leave would leave the department with 0 coverage.
    """
    user = db["users"].find_one({"id": user_id})
    if not user: return {"has_conflict": False, "reason": "User not found."}
    
    # Parse date to obtain day of week
    try:
        date_obj = datetime.strptime(request_date_str, "%Y-%m-%d")
        day_name = date_obj.strftime("%A")
    except ValueError:
        day_name = request_date_str # fallback if already a day string
        
    role = user["role"]
    dept = user["department"]
    schedule = db["schedules"].find_one({"role": role, "department": dept})
    
    if not schedule or "schedule" not in schedule:
        return {"has_conflict": False, "reason": "No schedule generated yet."}
        
    day_shifts = schedule["schedule"].get(day_name, {})
    is_scheduled = False
    for shift_num, assigned_name in day_shifts.items():
        if assigned_name == user["name"]:
            is_scheduled = True
            
    if not is_scheduled:
        return {"has_conflict": False, "reason": "Not scheduled on this day."}
        
    # Check coverage
    total_assigned_today = len(day_shifts.keys())
    if total_assigned_today <= 1:
        return {"has_conflict": True, "reason": "Approving this leave causes ZERO coverage for this department."}
        
    return {"has_conflict": True, "reason": "Employee is scheduled for a shift on this day, but coverage is viable."}

def find_replacement(user_id, request_date_str):
    """
    Mini-CSP to find a valid replacement colleague. 
    Constraint: NOT already assigned, max_shifts not exceeded, NOT their preferred off day.
    """
    user = db["users"].find_one({"id": user_id})
    if not user: return None
    
    try:
        day_name = datetime.strptime(request_date_str, "%Y-%m-%d").strftime("%A")
    except ValueError:
        day_name = request_date_str

    role = user["role"]
    dept = user["department"]
    schedule = db["schedules"].find_one({"role": role, "department": dept})
    
    if not schedule: return None
    
    # 1. Identify which shift the user is on
    day_shifts = schedule["schedule"].get(day_name, {})
    user_shift = None
    for shift_num, assigned_name in day_shifts.items():
        if assigned_name == user["name"]:
            user_shift = shift_num
            break
            
    if not user_shift: return None # User isn't scheduled today
    
    # 2. Get colleagues
    colleagues = list(db["users"].find({"department": dept, "role": role, "id": {"$ne": user_id}}))
    
    # 3. Filter candidates
    for coll in colleagues:
        # Check preferred off day
        if coll.get("preferred_off_day") == day_name:
            continue
            
        # Check if they are already working in the other shift on this day
        already_working_today = False
        for s_num, a_name in day_shifts.items():
            if a_name == coll["name"]:
                already_working_today = True
        if already_working_today:
            continue
            
        # Check max shifts
        current_shifts = 0
        for d, s in schedule["schedule"].items():
            for s_num, a_name in s.items():
                if a_name == coll["name"]:
                    current_shifts += 1
        
        if current_shifts >= coll.get("max_shifts_per_week", 5):
            continue
            
        # Passed all constraints
        return {"colleague": coll["name"], "shift": user_shift, "day": day_name}
        
    return None

def submit_leave_request(user_id, name, department, request_date, duration="1 Day"):
    existing = db["requests"].find_one({"id": user_id, "Dates": request_date})
    if existing: return False
    
    # Run conflict detection
    conflict_data = check_leave_conflict(user_id, request_date)
    
    data = {
        "id": user_id,
        "Name": name,
        "Dept": department,
        "Dates": [request_date],
        "Duration": duration,
        "Status": "Pending",
        "has_conflict": conflict_data["has_conflict"],
        "conflict_reason": conflict_data["reason"],
        "Email": "visvafelix2005@gmail.com",
    }
    db["requests"].insert_one(data)
    return True

def get_pending_requests():
    return list(db["requests"].find({"Status": "Pending"}))

def update_request_status(request_id, action, request_dates):
    """
    Approves or denies a leave. 
    If approved, runs auto-replacement and rewrites the schedule if a replacement exists.
    """
    request_doc = db["requests"].find_one({"_id": request_id})
    if not request_doc: return False
    
    user_id = request_doc["id"]
    new_status = "Approved" if action == "accept" else "Denied"
    db["requests"].update_one({"_id": request_id}, {"$set": {"Status": new_status}})
    
    # Post-approval replacement execution
    if action == "accept":
        # Loop through dates
        for date_str in request_dates:
            replacement_info = find_replacement(user_id, date_str)
            if replacement_info:
                # Automate swap in schedules DB
                user = db["users"].find_one({"id": user_id})
                role = user["role"]
                dept = user["department"]
                day_name = replacement_info["day"]
                shift_name = replacement_info["shift"]
                new_candidate = replacement_info["colleague"]
                
                # Retrieve existing schedule
                sched_doc = db["schedules"].find_one({"role": role, "department": dept})
                if sched_doc:
                    # Update local ref
                    sched_doc["schedule"][day_name][shift_name] = new_candidate
                    db["schedules"].update_one({"_id": sched_doc["_id"]}, {"$set": {"schedule": sched_doc["schedule"]}})
                    # Record replacement in request
                    db["requests"].update_one({"_id": request_id}, {"$push": {"replacement": new_candidate}})
    
    # Notification
    subject = "Update On Your Leave Request"
    dates_str = ",".join(request_dates) if isinstance(request_dates, list) else request_dates
    body = f"Dear User,\n\nYour leave request for {dates_str} has been {new_status}.\n\nThank you."
    send_email(subject, body, "visvafelix2005@gmail.com")
    
    return new_status

# --- Shift Swapping ---

def request_shift_swap(requester_id, target_name, shift_date, shift_num):
    user = db["users"].find_one({"id": requester_id})
    data = {
        "requester_id": requester_id,
        "requester_name": user["name"],
        "target_name": target_name,
        "shift_date": shift_date,
        "shift_num": shift_num,
        "Status": "Pending"
    }
    db["swap_requests"].insert_one(data)
    return True

def get_pending_swaps():
    return list(db["swap_requests"].find({"Status": "Pending"}))

def approve_swap(swap_id):
    swap_doc = db["swap_requests"].find_one({"_id": swap_id})
    if not swap_doc: return False
    
    # Get user details
    requester = db["users"].find_one({"id": swap_doc["requester_id"]})
    if not requester: return False
    
    try:
        day_name = datetime.strptime(swap_doc["shift_date"], "%Y-%m-%d").strftime("%A")
    except ValueError:
        day_name = swap_doc["shift_date"]
        
    role = requester["role"]
    dept = requester["department"]
    sched_doc = db["schedules"].find_one({"role": role, "department": dept})
    
    if sched_doc:
        # Perform swap directly
        sched_doc["schedule"][day_name][swap_doc["shift_num"]] = swap_doc["target_name"]
        db["schedules"].update_one({"_id": sched_doc["_id"]}, {"$set": {"schedule": sched_doc["schedule"]}})
        db["swap_requests"].update_one({"_id": swap_id}, {"$set": {"Status": "Approved"}})
        return True
    return False

# --- Core Schedule Loading ---

def save_schedule(role, schedule_data, fairness_scores):
    db["schedules"].delete_many({"role": role})
    for dept, data in schedule_data.items():
        db["schedules"].insert_one({"role": role, "department": dept, "schedule": data, "fairness_scores": fairness_scores.get(dept, {})})

def get_schedule(role):
    schedules = list(db["schedules"].find({"role": role}))
    result = {}
    for s in schedules:
        result[s["department"]] = {
            "schedule": s["schedule"],
            "fairness_scores": s.get("fairness_scores", {})
        }
    return result

def get_personal_schedule(name):
    schedules = list(db["schedules"].find({}, {"_id": 0}))
    personal = {}
    for entry in schedules:
        dept = entry["department"]
        dept_schedule = entry.get("schedule", {})
        for day, shifts in dept_schedule.items():
            for shift_name, assigned_employee in shifts.items():
                if assigned_employee == name:
                    if day not in personal:
                        personal[day] = []
                    personal[day].append(f"{shift_name} ({dept})")
    return personal

# --- Analytics ---
def get_analytics_data():
    """
    Returns data aggregations for Admin charts.
    """
    ans = {
        "shift_distribution": {},
        "leave_frequency": {},
        "coverage": {}
    }
    
    # Shift distribution (from Fairness scores)
    schedules = list(db["schedules"].find({}))
    for s in schedules:
        scores = s.get("fairness_scores", {})
        for emp, count in scores.items():
            ans["shift_distribution"][emp] = count
            
    # Leave frequency per department
    reqs = db["requests"].find()
    for r in reqs:
        d = r.get("Dept", "Unknown")
        ans["leave_frequency"][d] = ans["leave_frequency"].get(d, 0) + 1
        
    # Department Coverage mapping
    for s in schedules:
        dept = s["department"]
        ans["coverage"][dept] = {}
        for day, shifts in s.get("schedule", {}).items():
            ans["coverage"][dept][day] = len(shifts.keys())
            
    return ans

# --- Mailing ---
def send_email(subject, body, to_address="visvafelix2005@gmail.com"):
    smtp_server = 'smtp.gmail.com'
    smtp_port = 587
    smtp_username = os.getenv("EMAIL_SENDER", "no.reply.hosschman@gmail.com")
    smtp_password = os.getenv("EMAIL_PASSWORD", "ywwx wykh gkkk bkkd")
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        message = MIMEMultipart()
        message['From'] = smtp_username
        message['To'] = to_address
        message['Subject'] = subject
        message.attach(MIMEText(body, 'plain'))
        server.sendmail(smtp_username, to_address, message.as_string())
        server.quit()
    except Exception as e:
        print(f"Failed to send email: {e}")
