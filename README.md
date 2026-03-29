# 🏥 Hospital Workforce Scheduling System (HWSMS)

A cutting-edge, artificial intelligence-powered workforce optimization tool natively built in Python utilizing **Streamlit** and **MongoDB**. The core of this system is a dedicated Constraint Satisfaction Problem (CSP) solver built to combat the logistical nightmare of scheduling massive amounts of Doctors and Nurses simultaneously without breaking human constraints (maximum hours, preferred off-days, and specific shift-time requests).

## 🧠 The AI Engine: Constraint Satisfaction Problem (CSP)
Traditional scheduling is hard-coded and static. This project utilizes true mathematical modeling to resolve shifts dynamically via `scheduler.py`.

### 1. Variables & Domains
The Variables in our CSP are defined as permutations of `(Day, Shift)`. For example, a single week contains 14 variables per department (7 days × 2 shifts). The **Domain** for each variable is the entire pool of staff within that specific department.
We immediately execute **Domain Pruning** by removing staff members from variables where they physically cannot work:
- If variable Day == `preferred_off_day`.
- If variable Shift != `preferred_shift` (unless preference is `"Any"`).

### 2. Deep Forward Checking
When the recursive algorithm places `Doctor A` into `Monday - Shift 1`, it executes **Forward Checking**. It jumps ahead into the unassigned variable `Monday - Shift 2` and physically rips `Doctor A` out of its domain. This severely narrows the recursive branching tree, preventing double-booking natively and drastically accelerating computational times.

### 3. Chronological Backtracking
If the tree traverses too deeply and finds a variable `(Tuesday, Shift 2)` that has **0 candidates** available (because everyone else has either maxed out their `max_shifts_per_week` or is taking a leave), it admits defeat. It climbs backward up the tree (**Backtracking**), undoes the previous assignment(s), restores their pruned domains, and attempts an alternative candidate permutation.

### 4. Fairness Redistribution Pass
Schedules can mathematically succeed but physically feel awful (one doctor working 6 shifts, another working 2). Upon a successful tree completion, the fairness array counts totals. If `max_shifts - min_shifts > 2`, the engine forces a post-processing **Fairness Pass**—it steals an overflow shift from the overworked employee and attempts to wedge the underworked employee into it, double-checking it breaks zero static constraints in the process.

## 🛠️ System Architecture

- `main.py` -> The gateway and routing matrix. Sleek dark-mode container housing the login states.
- `init_db.py` -> Generates the robust mockup data. Injects 52 uniquely randomized staff members directly into MongoDB to thoroughly saturate and stress-test the CSP logic.
- `scheduler.py` -> The raw brain of the operation containing the Forward Checking & Backtracking pipelines. 
- `database.py` -> Natively interfaces with MongoDB `hwsms_db`. Houses complex operations like `find_replacement()`, an isolated mini-CSP that scours a department to intelligently replace a suddenly empty shift slot if an admin approves a peer's time-off.
- `admin_dashboard.py` -> Rendered as the Command Center. Contains color-coded HTML matrices of the master schedule, and conflict warnings displaying zero-coverage risks in pending leaves natively calculated by the DB.
- `employee_portal.py` -> A stunning front-end 7-Day calendar UI utilizing `st.markdown`. Contains shift-swap request mechanics so peers can mathematically propose alterations.

## 🚀 Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Boot Local Database Services
Ensure you have MongoDB Community Server actively running on your machine (specifically on `localhost:27017` via Windows Services or `mongod`).

### 3. Initialize & Stress Data
Wipe and re-seed the massive datasets to guarantee constraints are met:
```bash
python init_db.py
```

### 4. Launch Sub-routine
```bash
streamlit run main.py
```
