**Hospital Workforce Scheduling**

**Management System**

**HWSMS \| Complete Technical Reference**

*Forward Checking \| Backtracking \| Fairness Redistribution \|
Auto-Replacement CSP*


# 1. Project Overview

The Hospital Workforce Scheduling Management System (HWSMS) is a
full-stack web application that automates the generation, management,
and real-time monitoring of hospital staff schedules across multiple
departments. The system is designed specifically for hospital
environments where Doctors and Nurses must be scheduled across
departments such as Cardiology, Neurology, Oncology, and Pediatrics
while satisfying a large number of simultaneous individual and
organisational constraints.

The core scheduling engine is built on a Constraint Satisfaction Problem
(CSP) formulation augmented with Forward Checking, recursive
Backtracking, and a post-generation Fairness Redistribution pass. These
three algorithmic layers work in sequence to ensure that generated
schedules are not only constraint-valid but also equitable across all
staff members. Scheduling data is fully persisted in MongoDB and
survives server restarts, enabling the system to operate statelessly
across sessions.

The application is split into two distinct portals. The Admin portal
provides schedule generation controls, leave request management with
automated conflict detection and replacement scheduling, shift swap
approval, and a multi-dimensional analytics dashboard. The Employee
portal gives each staff member a personalised visual 7-day calendar, a
leave submission form with embedded conflict awareness, and a peer shift
swap request interface.

## 1.1 Problem Statement

Manual hospital scheduling is an NP-hard combinatorial optimisation
problem. A human scheduler must simultaneously respect individual
rest-day preferences, shift type preferences, maximum weekly workload
constraints, department minimum coverage requirements, and the cascading
effects of leave approvals on coverage. As the number of staff and
departments scales, the solution space grows exponentially and the
probability of human error increases proportionally. HWSMS reduces this
to an automated, deterministic, constraint-verified computation that
produces valid schedules in seconds.

## 1.2 Core Capabilities

-   Automated 7-day two-shift schedule generation using a CSP solver
    with domain pruning and recursive backtracking

-   Real constraint satisfaction sourced from per-employee database
    fields: preferred_off_day, preferred_shift, and max_shifts_per_week
    are read at generation time and enforced throughout assignment

-   Forward Checking: after each shift assignment, all remaining slot
    domains are immediately pruned to remove candidates who would
    violate constraints if assigned next

-   Backtracking: when a slot\'s domain is exhausted after pruning, the
    solver reverses its most recent assignment and tries the next
    candidate, preventing the solver from getting stuck

-   Fairness Redistribution: a post-generation pass detects shift-count
    imbalances greater than two shifts across staff in the same
    department and performs constraint-verified swaps to close the gap

-   Auto-Replacement CSP: when an admin approves a leave, a mini-CSP
    searches for a valid colleague who satisfies all scheduling
    constraints and rewrites the master schedule automatically

-   Conflict Detection: leave submissions trigger an immediate check
    against the live schedule to flag whether the employee is already
    assigned on that day and whether approval would leave the department
    with zero coverage

-   Shift Swap Workflow: employees submit peer swap requests which are
    queued for admin review; approved swaps directly overwrite the
    master schedule

-   Analytics Dashboard: shift fairness bar chart sourced from fairness
    scores, leave frequency per department, and a colour-coded coverage
    heatmap

-   Email notification via Gmail SMTP dispatched on every leave status
    change

-   Role-based portal routing with Streamlit session state: Admin role
    sees the command centre dashboard, Doctor and Nurse roles see the
    personalised employee portal

-   Futuristic dark-mode Streamlit theme with custom CSS injected at
    startup

## 1.3 Technology Stack

  ------------------------------------------------------------------------
  **Component**   **Technology**   **Role in the System**
  --------------- ---------------- ---------------------------------------
  Web Framework   Streamlit        UI rendering, session state management,
                                   form handling, and portal routing
                                   between admin and employee views

  Language        Python 3.x       All application logic, algorithm
                                   implementation, database access, and
                                   email dispatch

  Database        MongoDB via      Persistent storage for all five
                  PyMongo          collections: users, schedules,
                                   requests, swap_requests, departments

  Scheduling      Custom CSP       Forward Checking and Backtracking
  Algorithm                        solver producing constraint-valid,
                                   fairness-adjusted shift schedules

  Data Display    pandas           Tabular formatting of schedule data,
                                   analytics aggregation, and styled
                                   dataframe rendering in Streamlit

  Email           smtplib with     Automated plain-text notifications
                  Gmail SMTP       dispatched on leave status changes

  Configuration   python-dotenv    Environment variable loading for
                                   MongoDB URI, database name, and email
                                   credentials from a .env file
  ------------------------------------------------------------------------

# 2. System Architecture

HWSMS follows a layered architecture with clear separation between
presentation, application, and data concerns. The presentation layer is
handled entirely by Streamlit, which manages both routing and UI
rendering without a separate frontend build step. The application layer
contains business logic and algorithm code distributed across Python
modules. The data layer is a MongoDB instance accessed exclusively
through a single database abstraction module, ensuring that no other
module directly touches the database driver.

## 2.1 Module Map

  ---------------------------------------------------------------------------
  **File**             **Layer**      **Primary Responsibility**
  -------------------- -------------- ---------------------------------------
  main.py              Presentation / Entry point. Applies CSS theme, manages
                       Routing        authentication session state, renders
                                      the login form, and routes
                                      authenticated users to the correct
                                      portal based on their role field.

  admin_dashboard.py   Presentation / Admin-facing UI. Four-tab interface
                       Application    covering schedule generation and
                                      rendering, leave request cards with
                                      conflict display, swap queue, and
                                      analytics visualisations.

  employee_portal.py   Presentation / Employee-facing UI. Three-tab interface
                       Application    covering the 7-day visual calendar with
                                      shift summary metrics, leave submission
                                      form, and shift swap request form.

  scheduler.py         Application /  Core CSP engine. Reads real constraints
                       Algorithm      from the database, runs the Forward
                                      Checking and Backtracking solver for
                                      each department, runs the Fairness
                                      Redistribution pass, and calls
                                      save_schedule() to persist results.

  database.py          Data /         Single data access layer. All MongoDB
                       Application    reads and writes pass through this
                                      module. Also contains the conflict
                                      detection engine, auto-replacement CSP,
                                      swap management functions, analytics
                                      aggregation, and email dispatch.

  init_db.py           Data / Setup   One-time seeding script. Drops and
                                      recreates all collections, inserts
                                      staff documents including all
                                      constraint fields, and seeds realistic
                                      preference distributions across staff.
  ---------------------------------------------------------------------------

## 2.2 Data Flow: Schedule Generation

The following sequence describes the complete data path when an admin
triggers schedule generation:

1.  Admin clicks Generate Docs Schedule or Generate Nurses Schedule in
    admin_dashboard.py.

2.  admin_dashboard.py calls generate_schedule(role) from scheduler.py.

3.  scheduler.py calls get_all_users_by_role(role) from database.py,
    which returns all staff documents including preferred_off_day,
    preferred_shift, and max_shifts_per_week fields.

4.  The CSP solver organises staff by department, sorts each department
    by experience descending, and constructs a domain dictionary mapping
    each of the 14 slot identifiers to its list of eligible candidates.

5.  For each department, the solver runs the assignment loop. At each
    slot it prunes the domain using Forward Checking, assigns a
    candidate, and recurses. On domain exhaustion it backtracks.

6.  After all slots are filled, the Fairness Redistribution pass counts
    assignments per employee, detects imbalances, and performs
    constraint-verified swaps.

7.  The formatted schedule and per-employee fairness scores are passed
    to save_schedule() in database.py, which deletes the previous
    schedule for that role and writes new documents to the schedules
    collection.

8.  admin_dashboard.py calls st.rerun() to refresh the UI, which
    re-fetches get_schedule() and re-renders the HTML schedule table.

## 2.3 Data Flow: Leave Request Lifecycle

9.  Employee selects a date in the Request Leave tab and submits the
    form.

10. employee_portal.py calls submit_leave_request() in database.py.

11. submit_leave_request() checks for an existing request on the same
    date by the same user. If one exists, it returns False and no
    document is inserted.

12. check_leave_conflict() is called with the user ID and date. It reads
    the schedules collection to determine whether the employee is
    assigned on that day and whether the department would have zero
    coverage if the leave were approved. It returns a dictionary with
    has_conflict and conflict_reason.

13. The request document is inserted into the requests collection with
    the conflict metadata embedded in the document.

14. Admin views the pending request in the Leave Requests tab. The
    conflict warning is displayed in colour: red for critical
    zero-coverage conflicts, green for viable cases.

15. Admin clicks Approve and Automate Swap. update_request_status() in
    database.py sets the Status field to Approved.

16. For each date in the request, find_replacement() is called. It runs
    a mini-CSP over colleagues in the same department, finds the first
    valid replacement, updates the schedules document, and records the
    replacement name in the requests document.

17. send_email() dispatches a plain-text notification via Gmail SMTP.

# 3. Algorithm Deep Dive: The CSP Scheduler

This section documents the scheduling algorithm in complete technical
detail. The algorithm is implemented in scheduler.py and is the
intellectual core of the system. It applies three techniques in
sequence: domain initialisation with experience-weighted candidate
ordering, Forward Checking with same-day and weekly-limit pruning, and
recursive Backtracking. A Fairness Redistribution pass runs after the
main solver and is described separately.

## 3.1 Constraint Satisfaction Problems: Foundational Concepts

A Constraint Satisfaction Problem is defined by three components: a
finite set of variables, a domain of possible values for each variable,
and a set of constraints specifying which combinations of variable-value
assignments are valid. The goal is to find a complete assignment --- one
value per variable --- such that every constraint is satisfied
simultaneously.

Solving a CSP by naive enumeration is computationally intractable for
large problems because the number of possible assignments grows
exponentially with the number of variables. Practical CSP solvers use
constraint propagation and intelligent search to prune the search space
before exploring it. Forward Checking is one such propagation technique,
and Backtracking is the systematic search strategy that pairs with it.

In HWSMS the variables are the 14 shift slots per department per week,
numbered as Monday Shift 1, Monday Shift 2, Tuesday Shift 1, and so on
through Sunday Shift 2. The domain of each slot is the list of employees
in that department who are eligible to fill it. The constraints are
described in the following section.

## 3.2 Constraint Definitions

  -------------------------------------------------------------------------------------
  **Constraint**        **Type**   **Source Field**      **How Enforced**
  --------------------- ---------- --------------------- ------------------------------
  No double-booking in  Hard       Derived from schedule Forward Checking: assigning E
  a single day                     structure             to Day_ShiftN immediately
                                                         removes E from Day_ShiftM for
                                                         all M not equal to N.

  Preferred off-day     Hard       preferred_off_day     Domain initialisation: the
  must be respected                                      employee is excluded from all
                                                         slots on their preferred
                                                         off-day before the solver
                                                         begins.

  Maximum shifts per    Hard       max_shifts_per_week   Forward Checking: when an
  week must not be                                       employee\'s assignment count
  exceeded                                               reaches their limit, they are
                                                         removed from all remaining
                                                         slot domains.

  Preferred shift       Soft       preferred_shift       Candidate ordering: employees
  number is honoured                                     whose preferred_shift matches
  where possible                                         the current slot\'s shift
                                                         number are moved to the front
                                                         of the domain list.

  Experience-weighted   Soft       experience            Department-level sort: staff
  selection                                              are sorted by experience
                                                         descending before domain
                                                         construction.
                                                         Higher-experience staff are
                                                         considered first.
  -------------------------------------------------------------------------------------

## 3.3 Domain Initialisation

Before the assignment loop begins for a department, the solver
constructs the initial domain for each of the 14 slot identifiers. For
each slot, the initial domain is built as follows:

18. All staff in the department are listed, sorted by experience
    descending. This ordering is preserved throughout the solving
    process.

19. Each employee is evaluated against their preferred_off_day. If the
    slot\'s day matches the employee\'s preferred off-day, that employee
    is excluded from this slot\'s domain entirely at initialisation
    time, before the solver even begins. This means the off-day
    constraint is enforced through domain restriction rather than during
    constraint checking, which is computationally cheaper.

20. The remaining candidates are sorted so that employees whose
    preferred_shift matches the current slot\'s shift number appear
    first. This is a soft-constraint ordering: the solver will try
    preferred-shift candidates first but will fall through to others if
    needed.

The result is a dictionary mapping each slot identifier to an ordered
list of eligible candidates. This is the starting state of the search.

## 3.4 The Assignment Loop and Forward Checking

The solver iterates over the 14 slot identifiers in order. For each slot
it selects the first candidate from the slot\'s current domain and
tentatively assigns them. This tentative assignment then immediately
triggers Forward Checking.

Forward Checking propagates the consequences of the current assignment
to the domains of all remaining unassigned slots. In HWSMS this
propagation enforces two constraints:

**Same-Day Exclusion (No Double-Booking)**

When employee E is assigned to slot Day_X_ShiftN, the solver removes E
from the domain of slot Day_X_ShiftM for all values of M that are not
equal to N. Since each day has exactly two shifts, assigning E to Shift
1 on a given day removes E from the domain of Shift 2 on the same day.
This is computed by iterating over all remaining slots, identifying
those that share the same day name, and filtering out E from their
domain lists.

**Weekly Limit Enforcement**

Each assignment increments an internal assignment counter for the
assigned employee. If that counter reaches the employee\'s
max_shifts_per_week value, the solver removes that employee from the
domains of all remaining unassigned slots across all days for that
department. This enforces the weekly maximum as a hard constraint
through domain pruning rather than through post-hoc validation.

The key insight of Forward Checking is that constraint violations are
detected before the solver reaches the slot where they would occur. This
transforms what would be a runtime failure into a domain restriction
applied at assignment time, which avoids exploring entire subtrees of
the search space that are guaranteed to be invalid.

## 3.5 Backtracking

Backtracking is the mechanism by which the solver recovers from dead
ends. A dead end occurs when the current slot\'s domain has been reduced
to empty --- every candidate has been pruned by Forward Checking from
previous assignments. When this happens, the solver cannot make any
assignment for the current slot and must undo a previous decision.

The backtracking procedure works as follows. The solver maintains a
stack of assignments made so far. When a dead end is encountered, it
pops the most recent assignment from the stack, restores the domain
state that existed before that assignment was made (including reversing
all Forward Checking prunings that resulted from it), and then attempts
the next candidate in that slot\'s domain. If all candidates for that
slot have been tried and all lead to dead ends, the solver backtracks
again to the slot before it.

This is classical chronological backtracking. In the worst case it
explores the entire search space, but in practice the combination with
Forward Checking means that most dead ends are detected very early ---
often after only a few assignments --- because Forward Checking has
already eliminated the problematic candidates from downstream domains.
The practical effect is that the solver rarely needs to backtrack more
than one or two levels in typical hospital scheduling instances.

## 3.6 Worked Example: A Three-Employee, Two-Shift Day

Consider a department with three employees: Alice (max 5 shifts, off-day
Sunday, preferred shift 1), Bob (max 4 shifts, off-day Saturday,
preferred shift 2), and Carol (max 5 shifts, off-day Wednesday,
preferred shift 1). The solver is processing Monday.

Monday Shift 1 domain after initialisation: \[Alice, Carol, Bob\] (Alice
and Carol prefer Shift 1, Bob prefers Shift 2 and is moved to the end).

The solver assigns Alice to Monday Shift 1. Forward Checking fires:
Alice\'s counter becomes 1. Alice is removed from the domain of Monday
Shift 2. If Alice\'s counter had reached 5, she would also be removed
from all remaining slots across the week.

Monday Shift 2 domain after Forward Checking: \[Bob, Carol\] (Alice
removed; Bob is now first because he prefers Shift 2).

The solver assigns Bob to Monday Shift 2. Bob\'s counter becomes 1. Bob
is removed from all other Monday slots (none remain) and from all
remaining slots if his counter had reached his limit.

Monday is now fully assigned. Alice and Bob both have 1 shift counted.
The solver moves to Tuesday and repeats the process with the pruned
domains.

## 3.7 Fairness Redistribution Pass

After the CSP solver completes assignment for all 14 slots in a
department, the resulting schedule is constraint-valid but may be
inequitable. Because the solver assigns staff in experience order and
stops assigning an employee once their slot is filled, early-experience
staff tend to accumulate more shifts than less-experienced colleagues
who may have had their slots filled by others before they were reached.

The Fairness Redistribution pass runs after the main solver and operates
on the completed schedule. It proceeds as follows:

21. Count the total number of shifts assigned to each employee in the
    department.

22. Identify the most-assigned employee (call their count H) and the
    least-assigned employee (call their count L).

23. If H minus L is greater than 2, the schedule is considered
    imbalanced and redistribution begins.

24. Iterate over the most-assigned employee\'s shifts. For each shift,
    check whether the least-assigned employee could take that shift
    without violating any constraint: their preferred_off_day must not
    match that day, their current total must be below their
    max_shifts_per_week, and they must not already be assigned on that
    day in either shift.

25. If a valid swap target is found, update the schedule to replace the
    most-assigned employee in that slot with the least-assigned
    employee. Update both employees\' counts.

26. Recalculate H and L. If the gap still exceeds 2, repeat from step 4.
    Continue until the gap is 2 or less, or until no further valid swaps
    can be found.

After redistribution completes, the final shift count per employee is
stored as the fairness_scores dictionary. This dictionary is saved
alongside the schedule document in MongoDB and is surfaced in both the
Admin Analytics tab (as a bar chart showing shift distribution across
all staff) and in each employee\'s personal Shift Summary (as a metric
comparing their shift count to their department average).

## 3.8 Auto-Replacement CSP

The auto-replacement system is a second, lighter CSP that executes
inside database.py at the moment an admin approves a leave request. Its
function is to find a valid substitute for the absent employee\'s
vacated shift and rewrite the master schedule without introducing any
new constraint violations.

The replacement CSP operates as follows:

27. Receive the absent employee\'s user ID and the requested leave date
    string.

28. Parse the date string to obtain the day name. Look up the
    employee\'s current schedule entry to identify which shift they are
    assigned to on that day.

29. Retrieve all colleagues in the same department and role from the
    users collection.

30. For each colleague, evaluate three constraints in order. First:
    their preferred_off_day must not match the leave day. Second: they
    must not already be assigned to any shift on that day in the current
    schedule (checked by inspecting the schedule document\'s day entry).
    Third: their current total shift count as determined from the
    schedule document must be strictly less than their
    max_shifts_per_week.

31. The first colleague who passes all three constraints is selected.
    The schedules document is updated using a targeted MongoDB update
    operation that overwrites the absent employee\'s name with the
    replacement\'s name in the specific day and shift slot.

32. The replacement name is appended to the replacement array in the
    leave request document for audit purposes.

If no valid replacement is found because all colleagues are already
working that day or are at their weekly limit, the function returns
None. The schedule slot retains the original employee\'s name and the
admin is informed via the UI that no automatic replacement was possible.

# 4. Database Schema

HWSMS uses MongoDB with five collections. All collections are dropped
and recreated by init_db.py. The following sections describe the
structure of each collection as it exists after seeding and during
normal operation.

## 4.1 Collection: users

Stores all system users. The Admin user has only identity fields. All
Doctor and Nurse users include the three constraint fields that the CSP
solver reads at generation time.

  ----------------------------------------------------------------------------
  **Field**             **Type**   **Notes**
  --------------------- ---------- -------------------------------------------
  id                    String     Unique user identifier. Format: A001 for
                                   Admin, D001-D999 for Doctors, N001-N999 for
                                   Nurses.

  name                  String     Full display name used for authentication,
                                   schedule matching, and all UI labels. Must
                                   be unique across the collection.

  password              String     Plaintext password for authentication
                                   lookup via authenticate_user().

  role                  String     Controls portal routing. One of: Admin,
                                   Doctor, Nurse.

  department            String     Department membership. One of: Cardiology,
                                   Neurology, Oncology, Pediatrics. Null for
                                   Admin users.

  experience            Integer    Years of experience. Used only for sorting
                                   within a department before CSP assignment.
                                   Not enforced as a constraint.

  email                 String     Notification email address. Currently all
                                   staff share one test address in the seeded
                                   data.

  Assigned              Boolean    Legacy flag retained from the original
                                   implementation. Reserved for future
                                   multi-round scheduling use.

  preferred_off_day     String     Day name the employee prefers not to work.
                                   Enforced as a hard constraint through
                                   domain initialisation. Example: Saturday.

  preferred_shift       Integer or Preferred shift number (1 or 2) or the
                        String     string Any. Used for soft-constraint
                                   candidate ordering within a slot\'s domain.

  max_shifts_per_week   Integer    Hard upper bound on total shifts per
                                   generated schedule. Enforced through
                                   Forward Checking. Default value is 5.
  ----------------------------------------------------------------------------

## 4.2 Collection: schedules

One document per department per role. Written atomically by
save_schedule(): the entire collection of documents for the given role
is deleted before new documents are inserted, ensuring no stale data
persists.

  ---------------------------------------------------------------------------
  **Field**         **Type**   **Notes**
  ----------------- ---------- ----------------------------------------------
  role              String     The role this schedule covers. Doctor or
                               Nurse.

  department        String     The department this document covers. One
                               document exists per department per role after
                               generation.

  schedule          Object     Nested structure: day name maps to an object
                               whose keys are shift names (Shift 1, Shift 2)
                               and whose values are the assigned employee\'s
                               display name. Example: { Monday: { Shift 1:
                               Dr. Visva, Shift 2: Dr. CarDoc1 } }

  fairness_scores   Object     Maps employee display name to their total
                               assigned shift count after the Fairness
                               Redistribution pass. Used in analytics and employee
                               summary metrics.
  ---------------------------------------------------------------------------

## 4.3 Collection: requests

One document per leave request. Created at submission time with conflict
metadata embedded. Updated in place at approval or denial.

  ---------------------------------------------------------------------------
  **Field**         **Type**    **Notes**
  ----------------- ----------- ---------------------------------------------
  id                String      Requesting employee\'s user ID. Used to look
                                up their schedule entry during conflict
                                detection and replacement search.

  Name              String      Employee display name for UI rendering.

  Dept              String      Department name for UI rendering and leave
                                frequency analytics aggregation.

  Dates             Array of    List of date strings in YYYY-MM-DD format.
                    Strings     The replacement CSP iterates over this array
                                at approval time.

  Duration          String      Human-readable label (1 Day, 2 Days, 3 Days).
                                Stored for display only; does not currently
                                affect the number of Dates entries.

  Status            String      Current lifecycle state. One of: Pending,
                                Approved, Denied.

  has_conflict      Boolean     Computed at submission time by
                                check_leave_conflict(). True if the employee
                                is scheduled on the requested day.

  conflict_reason   String      Human-readable explanation from
                                check_leave_conflict(). Displayed in the
                                admin leave card as a coloured warning.

  Email             String      Notification target address. Currently
                                hardcoded to the test address at submission
                                time.

  replacement       Array of    Populated after approval by the
                    Strings     auto-replacement CSP. Contains the display
                                names of selected replacements, one per date
                                in Dates. Empty if no replacement was found.
  ---------------------------------------------------------------------------

## 4.4 Collection: swap_requests

One document per shift swap request. Created by request_shift_swap()
when an employee submits a swap through the employee portal. Updated to
Approved by approve_swap() when an admin acts on it.

  --------------------------------------------------------------------------
  **Field**        **Type**    **Notes**
  ---------------- ----------- ---------------------------------------------
  requester_id     String      User ID of the employee initiating the swap.

  requester_name   String      Display name of the requesting employee.
                               Looked up at submission time from the users
                               collection.

  target_name      String      Display name of the colleague the requester
                               wants to swap with.

  shift_date       String      Day name of the shift slot to be swapped.
                               Derived from the employee\'s selected shift
                               label in the portal.

  shift_num        String      Shift identifier for the slot to be swapped.
                               One of: Shift 1, Shift 2.

  Status           String      One of: Pending, Approved. Pending swaps
                               appear in the admin Swap Requests tab.
  --------------------------------------------------------------------------

# 5. Module Reference

## 5.1 scheduler.py

Contains the public generate_schedule() function and the full CSP
implementation including Forward Checking, Backtracking, and the
Fairness Redistribution pass.

### generate_schedule(role: str) -\> dict

Generates a complete 7-day two-shift schedule for all departments
containing staff of the given role. Reads staff and constraints from the
database, runs the CSP solver per department, runs the Fairness
Redistribution pass, and persists results via save_schedule(). Returns
the formatted schedule dictionary keyed by department name for immediate
use by the calling admin dashboard function.

### Domain Construction (internal)

For each department, staff are sorted by experience descending. For each
of the 14 slot identifiers, a domain list is built by filtering out
employees whose preferred_off_day matches the slot\'s day. Within each
domain, employees whose preferred_shift matches the slot\'s shift number
are moved to the front of the list to implement soft-constraint
ordering.

### CSP Assignment Loop (internal)

Iterates over slot identifiers. At each slot, selects the first
candidate from the current domain. Applies Forward Checking by removing
the assigned candidate from all same-day slots and from all remaining
slots if the candidate\'s weekly limit is reached. On domain exhaustion,
initiates backtracking by restoring the previous domain state and trying
the next candidate for the previous slot.

### Fairness Redistribution Pass (internal)

Counts assignments per employee after the CSP completes. If the gap
between the highest and lowest shift count exceeds two, iteratively
performs constraint-verified swaps from over-assigned to under-assigned
employees. Returns the final per-employee shift counts as the
fairness_scores dictionary.

## 5.2 database.py --- Function Reference

  -------------------------------------------------------------------------------------
  **Function**                        **Returns**   **Description**
  ----------------------------------- ------------- -----------------------------------
  authenticate_user(name, password)   Dict or None  Finds a user document matching both
                                                    name and password fields. Returns
                                                    the full document on success
                                                    including all constraint fields, or
                                                    None on failure.

  get_all_users_by_role(role)         List of Dict  Returns all user documents with the
                                                    given role. Used by the scheduler
                                                    to load staff and constraint fields
                                                    for schedule generation.

  get_colleagues(department, role)    List of Dict  Returns all staff sharing the given
                                                    department and role. Used by the
                                                    employee portal to populate the
                                                    shift swap target selectbox.

  get_departments()                   List of       Returns distinct department name
                                      String        values from the users collection.

  check_leave_conflict(user_id,       Dict          Parses the date string to a day
  date_str)                                         name. Reads the employee\'s
                                                    schedule entry. Returns a
                                                    dictionary with has_conflict
                                                    (boolean) and conflict_reason
                                                    (string). Reports both whether the
                                                    employee is scheduled and whether
                                                    approval would produce zero
                                                    coverage.

  find_replacement(user_id, date_str) Dict or None  Mini-CSP. Identifies which shift
                                                    the employee occupies on the given
                                                    day. Iterates over colleagues
                                                    evaluating preferred_off_day,
                                                    no-double-booking, and max_shifts
                                                    constraints. Returns the first
                                                    passing colleague\'s name, shift,
                                                    and day. Returns None if no valid
                                                    candidate exists.

  submit_leave_request(user_id, name, Boolean       Checks for a duplicate request on
  dept, date, duration)                             the same date. Calls
                                                    check_leave_conflict() and embeds
                                                    results in the document. Inserts
                                                    the request into MongoDB. Returns
                                                    False only if a duplicate exists.

  get_pending_requests()              List of Dict  Returns all request documents with
                                                    Status equal to Pending. Used by
                                                    the admin leave tab.

  update_request_status(request_id,   String        Sets Status to Approved or Denied.
  action, dates)                                    On approval, calls
                                                    find_replacement() per date,
                                                    updates the schedule document,
                                                    records the replacement, and
                                                    dispatches an email notification.
                                                    Returns the new status string.

  request_shift_swap(requester_id,    Boolean       Looks up the requester\'s display
  target_name, shift_date, shift_num)               name. Inserts a new swap_requests
                                                    document with Status Pending.

  get_pending_swaps()                 List of Dict  Returns all swap_requests documents
                                                    with Status Pending.

  approve_swap(swap_id)               Boolean       Fetches the swap document. Parses
                                                    the shift_date to a day name.
                                                    Overwrites the target slot in the
                                                    schedules collection with the
                                                    target employee\'s name. Updates
                                                    the swap status to Approved.
                                                    Returns False if the schedule
                                                    document cannot be found.

  save_schedule(role, schedule_data,  None          Deletes all existing schedules
  fairness_scores)                                  documents for the given role.
                                                    Inserts one new document per
                                                    department containing the schedule
                                                    and fairness_scores objects.

  get_schedule(role)                  Dict          Fetches all schedule documents for
                                                    the role. Returns a dictionary
                                                    keyed by department, each value
                                                    containing schedule and
                                                    fairness_scores sub-dictionaries.

  get_personal_schedule(name)         Dict          Scans all schedule documents.
                                                    Builds a dictionary keyed by day
                                                    name listing shift label and
                                                    department strings for every slot
                                                    where the given employee\'s name
                                                    appears.

  get_analytics_data()                Dict          Aggregates three data sources:
                                                    fairness_scores from all schedule
                                                    documents for shift distribution,
                                                    leave counts per department from
                                                    the requests collection, and shift
                                                    counts per day per department from
                                                    the schedule objects for the
                                                    coverage grid.

  send_email(subject, body,           None          Opens a TLS-encrypted SMTP
  to_address)                                       connection to smtp.gmail.com.
                                                    Authenticates with the configured
                                                    credentials. Sends a plain-text
                                                    MIMEMultipart message. Catches and
                                                    logs all exceptions without
                                                    raising.
  -------------------------------------------------------------------------------------

## 5.3 admin_dashboard.py --- Tab Reference

### Tab 1: Full Schedule

Two buttons trigger schedule generation for Doctors and Nurses
respectively by calling generate_schedule() with the appropriate role
string. A role selectbox below the buttons controls which schedule is
displayed. Schedule data is fetched via get_schedule() which returns the
nested department-schedule structure. The schedule is rendered as a raw
HTML table string built with inline styles matching the system dark
theme. Approved leaves are detected by querying the requests collection
for all Approved documents, parsing their dates to day names, and
cross-referencing them against the schedule to apply strikethrough
formatting and a leave indicator.

### Tab 2: Leave Requests

Fetches all pending requests via get_pending_requests(). Renders each
request as a collapsible Streamlit expander. Each expander card displays
the employee name, department, requested dates, duration, and the
conflict warning which is coloured red for zero-coverage conflicts and
green for viable conflicts. Two buttons per card invoke
update_request_status() with accept or deny action strings. Approval
triggers the full replacement pipeline. The page reruns after every
action to reflect the updated request status.

### Tab 3: Swap Requests

Fetches all pending swap requests via get_pending_swaps(). Renders each
as a styled div container using inline HTML. Displays the requester
name, target shift date and shift number, and the target colleague name.
A single approve button per request calls approve_swap() and reports
success or failure inline.

### Tab 4: Analytics

Calls get_analytics_data() once and uses its three sub-dictionaries to
render three visualisations. The shift distribution chart is a Streamlit
bar chart rendered from the shift_distribution dictionary sourced from
aggregated fairness_scores. The leave frequency chart is a Streamlit bar
chart of leave counts per department. The coverage heatmap is rendered
as a styled pandas dataframe where each cell value is the number of
shifts assigned in that department on that day, with red for zero,
yellow for one, and green for two.

## 5.4 employee_portal.py --- Tab Reference

### Tab 1: Visual Schedule

Calls get_personal_schedule() to retrieve the employee\'s assignments.
Renders a 7-column Streamlit column layout, one column per day of the
week. Each column renders shift cards as inline HTML with the system
dark-card style. Days with approved leaves show a leave badge. Off days
without a leave badge render a blank minimum-height placeholder. Below
the calendar, three Streamlit metric widgets display total shifts this
week (count of all assigned days), busiest day (the day with the most
shifts in the personal schedule), and a fairness metric comparing the
employee\'s shift count against the department average derived from the
fairness_scores field of their department\'s schedule document.

### Tab 2: Request Leave

A Streamlit form containing a date picker (minimum value today) and a
duration selectbox. On submission calls submit_leave_request(). Renders
a success message for new submissions and an error message for duplicate
date conflicts. Does not re-render the calendar; the employee must
switch tabs to see the effect.

### Tab 3: Shift Swap

Derives the employee\'s available shifts from their personal schedule by
parsing the shift label strings into day-shift pairs. Builds a target
colleague selectbox from get_colleagues() filtered to exclude the
current user. On form submission calls request_shift_swap(). Renders a
disabled submit button and an info message if the employee has no
assigned shifts to swap.

## 5.5 main.py

Calls st.set_page_config() to set the page title and icon and to enable
wide layout mode. Injects the global CSS theme string via st.markdown()
with unsafe_allow_html enabled. The CSS establishes the dark background
colour (hex 0b0c10), teal heading and accent colours (hex 66fcf1 and
45a29e), button hover effects with a glow transition, expander card
styling, and dataframe border-radius overrides. Manages the user key in
st.session_state. When no user is present, renders a centred heading and
a login form inside a middle column. On valid authentication via
authenticate_user(), stores the user document in session state and calls
st.rerun(). On subsequent loads, renders the sidebar with the logged-in
user name and a logout button, then routes to show_admin_dashboard() or
show_employee_portal() based on the role field.

## 5.6 init_db.py

Connects to MongoDB using MONGO_URI and DB_NAME from the .env file.
Drops and recreates five collections: users, departments, requests,
schedules, and swap_requests. Inserts one Admin document. Then iterates
over four department names and generates 6 Doctor documents and 6 Nurse
documents per department. Each generated staff document includes
preferred_off_day assigned by taking days\[i % 7\], preferred_shift
assigned by taking shifts\[i % 3\], and max_shifts_per_week alternating
between 5 and 6. This produces a realistic distribution of constraints
across the seeded staff. The script prints confirmation and the
total user count on completion.

# 6. Setup and Installation

## 6.1 Prerequisites

-   Python 3.9 or later installed and available on the system PATH

-   A running MongoDB instance accessible from the machine running the
    application. A local instance on mongodb://localhost:27017/ is the
    default. MongoDB Atlas with a connection string URI is also
    supported.

-   A Gmail account with an App Password configured. Standard account
    passwords do not work with smtplib because Gmail requires
    application-specific passwords for programmatic SMTP access.

-   pip for Python package installation

## 6.2 Installation

33. Clone or download the repository to a local directory.

34. Install Python dependencies:

> pip install streamlit pymongo python-dotenv pandas

35. Create a .env file in the project root directory with the following
    four variables:

> MONGO_URI=mongodb://localhost:27017/
>
> DB_NAME=hwsms_db
>
> EMAIL_SENDER=your.gmail.account@gmail.com
>
> EMAIL_PASSWORD=your_gmail_app_password

36. Run the database seeding script. This drops all existing collections
    and populates fresh data. It must be executed before the first
    launch and any time a full data reset is required:

> python init_db.py

37. Launch the Streamlit application:

> streamlit run main.py

38. Open the URL printed by Streamlit in a browser. The default is
    http://localhost:8501.

## 6.3 Recommended First-Run Sequence

39. Log in as Admin1 with password admin.

40. Navigate to the Full Schedule tab. Click Generate Docs Schedule and
    wait for the spinner to complete. Repeat with Generate Nurses
    Schedule.

41. Navigate to the Analytics tab. Verify that the shift distribution
    bar chart is populated with employee data and that the coverage
    heatmap shows non-zero values across departments and days.

42. Log out. Log in as Dr. Visva with password pass.

43. In the Visual Schedule tab, verify that the 7-day calendar shows
    assigned shifts and that the shift summary metrics display correct
    values.

44. Submit a leave request for any date using the Request Leave tab.

45. Log out. Log back in as Admin1. The Leave Requests tab should
    display the pending request with its conflict status badge.

46. Approve the request. Observe the confirmation message indicating
    whether a replacement was automatically found and scheduled.

# 7. Login Reference

The following credentials are seeded by init_db.py and available
immediately after running the script.

  ------------------------------------------------------------------------------
  **Account**           **Password**   **Role**    **Department**
  --------------------- -------------- ----------- -----------------------------
  Admin1                admin          Admin       Full system access, no
                                                   department

  Dr. Visva             pass           Doctor      Cardiology

  Dr. CarDoc1 through   pass           Doctor      Cardiology
  Dr. CarDoc6                                      

  Dr. NeuDoc1 through   pass           Doctor      Neurology
  Dr. NeuDoc6                                      

  Dr. OncDoc1 through   pass           Doctor      Oncology
  Dr. OncDoc6                                      

  Dr. PedDoc1 through   pass           Doctor      Pediatrics
  Dr. PedDoc6                                      

  Nurse CarNur1 through pass           Nurse       Cardiology
  Nurse CarNur6                                    

  Nurse NeuNur1 through pass           Nurse       Neurology
  Nurse NeuNur6                                    

  Nurse OncNur1 through pass           Nurse       Oncology
  Nurse OncNur6                                    

  Nurse PedNur1 through pass           Nurse       Pediatrics
  Nurse PedNur6                                    
  ------------------------------------------------------------------------------

# 8. Configuration Reference

  ------------------------------------------------------------------------------
  **Variable**     **Default Value**              **Effect**
  ---------------- ------------------------------ ------------------------------
  MONGO_URI        mongodb://localhost:27017/     MongoDB connection string.
                                                  Replace with an Atlas URI for
                                                  cloud-hosted deployments.

  DB_NAME          hwsms_db                       Name of the MongoDB database.
                                                  All five collections are
                                                  created within this database.

  EMAIL_SENDER     no.reply.hosschman@gmail.com   Gmail address used as the From
                                                  address for all notification
                                                  emails.

  EMAIL_PASSWORD   Hardcoded fallback in source   Gmail App Password for SMTP
                                                  authentication. Should be set
                                                  only in .env and the hardcoded
                                                  fallback removed before
                                                  distributing the codebase.
  ------------------------------------------------------------------------------

# 9. Extending the System

## 9.1 Adding a New Department

Add the department name string to the departments list in init_db.py.
Re-run the seeding script. The scheduler reads departments from staff
documents at generation time, so no changes to scheduler.py are needed.
The admin dashboard renders all departments returned by get_schedule()
automatically.

## 9.2 Adding New Constraints

Add the constraint field to user documents in init_db.py. Add the domain
exclusion logic to the domain initialisation phase in scheduler.py for
hard constraints, or to the candidate ordering logic for soft
constraints. Mirror any hard constraint check in the find_replacement()
function in database.py to keep the auto-replacement CSP consistent with
the main solver. Add the field to the get_analytics_data() aggregation
if it should surface in the Analytics tab.

## 9.3 Adding a New Role

Add user documents with the new role string in init_db.py. Add a
generate button for the new role in the Full Schedule tab of
admin_dashboard.py. The CSP solver and all database functions are
role-agnostic and handle new roles without modification as long as users
are correctly tagged in the database.

## 9.4 Replacing the Scheduling Algorithm

The scheduler is fully encapsulated behind the generate_schedule(role)
interface. Any alternative algorithm --- integer linear programming via
PuLP, a genetic algorithm, or a commercial CP solver --- can substitute
the existing CSP implementation by conforming to the same contract:
accept a role string, return a dictionary keyed by department with the
nested day-shift-employee structure, and call save_schedule() from
database.py with the results and a fairness scores dictionary.

# 10. Known Limitations and Design Notes

-   Passwords are stored in plaintext in MongoDB. This is acceptable for
    a prototype or academic demonstration environment but must be
    replaced with bcrypt hashing before any production or
    external-facing deployment.

-   The SMTP password appears as a hardcoded fallback default string in
    database.py. This value should be removed from the source file and
    supplied exclusively through the .env file. The current
    implementation will use the hardcoded value if the environment
    variable is absent.

-   The system operates on a single-week schedule model. Each
    generate_schedule() call produces an independent week and completely
    overwrites the previous schedule for that role. There is no
    multi-week continuity or rolling schedule support. Extending this
    would require adding a week identifier key to the schedule document
    structure.

-   The shift swap approval function approve_swap() performs a direct
    name substitution in the schedule without validating constraints for
    the target employee. A constraint check equivalent to the one in
    find_replacement() should be added to approve_swap() before the
    overwrite to prevent invalid swaps from passing through admin
    approval.

-   Email notifications are dispatched to a single hardcoded test
    address regardless of the individual employee\'s email field in the
    users collection. Production use requires replacing the hardcoded
    address with a lookup of the requesting employee\'s email field.

-   The leave duration field (1 Day, 2 Days, 3 Days) is stored for
    display purposes only. The current implementation processes only the
    single calendar date submitted in the date picker regardless of the
    selected duration value. Supporting multi-day leaves would require
    generating multiple date entries and running conflict detection and
    replacement for each one independently.

-   The coverage heatmap in the Analytics tab uses the pandas
    style.applymap() method which is deprecated in pandas 2.1 and later.
    It should be replaced with style.map() in environments running
    recent pandas versions to avoid deprecation warnings.

-   The schedule generation buttons in the admin dashboard do not
    prevent concurrent generation calls. In a multi-user environment,
    two admins clicking simultaneously could result in a race condition
    where both calls attempt to delete and re-insert schedule documents
    at the same time. A simple database-level lock or a Streamlit
    session flag would prevent this.

**Hospital Workforce Scheduling Management System**

*Built with Python, Streamlit, MongoDB, and a Constraint Satisfaction
Problem solver.*

github.com/VisvaV/Hospital-Workforce-Scheduling-System
