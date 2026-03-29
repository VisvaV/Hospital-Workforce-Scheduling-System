from database import get_all_users_by_role, get_departments, save_schedule

def generate_schedule(role):
    """
    Generates an automated schedule using the CSP algorithm with Forward Checking, 
    Backtracking, and a Fairness Pass redistribution algorithm.
    """
    staff = get_all_users_by_role(role)
    departments = {}
    
    # Organize staff by department
    for member in staff:
        dept = member.get("department")
        if dept:
            if dept not in departments:
                departments[dept] = []
            departments[dept].append(member)
            
    total_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    shifts_per_day = ["Shift 1", "Shift 2"]
    
    # The Variables in our CSP are tuples of (Day, Shift)
    variables = [(d, s) for d in total_days for s in shifts_per_day]
    
    final_schedule_db = {}
    final_fairness_db = {}

    for dept, dept_staff in departments.items():
        # --- DOMAIN INITIALIZATION ---
        # Map each variable to a list of valid candidate staff names
        domains = {}
        for var in variables:
            day, shift = var
            valid_candidates = []
            for emp in dept_staff:
                # Constraint: Employee cannot work on their preferred off day
                if emp.get("preferred_off_day") == day:
                    continue
                    
                # Constraint: Employee should match preferred shift 
                shift_num = 1 if shift == "Shift 1" else 2
                pref_shift = emp.get("preferred_shift")
                if pref_shift and pref_shift != "Any" and pref_shift != shift_num:
                    continue
                
                valid_candidates.append(emp["name"])
            domains[var] = valid_candidates
            
        assignments = {}
        # Track shifts assigned per employee to enforce max_shifts_per_week natively
        shift_counts = {emp["name"]: 0 for emp in dept_staff}
        
        # --- CSP BACKTRACKING SOLVER ---
        def backtrack(var_index):
            """
            Recursive Backtracking algorithm with Forward Checking pruning.
            """
            if var_index == len(variables):
                return True # All variables successfully assigned
            
            var = variables[var_index]
            day, shift = var
            
            # Iterate through the pruned domain for this variable
            for candidate in list(domains[var]):
                emp_obj = next((e for e in dept_staff if e["name"] == candidate), None)
                max_shifts = emp_obj.get("max_shifts_per_week", 5)
                
                # Check Dynamic Constraints 
                # Constraint: Prune if max shifts per week is exceeded
                if shift_counts[candidate] >= max_shifts:
                    continue
                    
                # Constraint: No double-booking in one day
                already_working = False
                for other_shift in shifts_per_day:
                    if other_shift != shift:
                        if assignments.get((day, other_shift)) == candidate:
                            already_working = True
                            break
                if already_working:
                    continue
                    
                # --- FORWARD CHECKING & ASSIGNMENT ---
                assignments[var] = candidate
                shift_counts[candidate] += 1
                
                # Forward Checking: Immediately prune this candidate from the remaining 
                # unassigned slots on the SAME DAY to narrow the search space
                pruned_var = (day, "Shift 2" if shift == "Shift 1" else "Shift 1")
                pruned_candidate = False
                if pruned_var in domains and candidate in domains[pruned_var]:
                    domains[pruned_var].remove(candidate)
                    pruned_candidate = True
                
                # Recurse deeper into the tree
                if backtrack(var_index + 1):
                    return True
                    
                # --- BACKTRACKING ---
                # If the above branch returned False, undo the assignment and restore domains
                del assignments[var]
                shift_counts[candidate] -= 1
                if pruned_candidate:
                    domains[pruned_var].append(candidate) # Restore domain
                    
            return False # Trigger backtrack chain
            
        success = backtrack(0)
        
        # --- FAIRNESS SCORING PASS ---
        if success:
            fairness_counts = {emp["name"]: 0 for emp in dept_staff}
            for (d, s), assigned_emp in assignments.items():
                fairness_counts[assigned_emp] += 1
                
            # Find the most overworked and underworked employees
            if fairness_counts:
                max_assigned_emp = max(fairness_counts, key=fairness_counts.get)
                min_assigned_emp = min(fairness_counts, key=fairness_counts.get)
                
                # If disparity is greater than 2 shifts, attempt redistribution
                if fairness_counts[max_assigned_emp] - fairness_counts[min_assigned_emp] > 2:
                    for (d, s), assigned_emp in assignments.items():
                        if assigned_emp == max_assigned_emp:
                            min_emp_obj = next((e for e in dept_staff if e["name"] == min_assigned_emp), None)
                            
                            # Validate constraints for the min_assigned_emp taking over this shift
                            if min_emp_obj.get("preferred_off_day") == d: continue
                            s_num = 1 if s == "Shift 1" else 2
                            if min_emp_obj.get("preferred_shift") not in [None, s_num]: continue
                            
                            # Prevent double-booking
                            already_working = False
                            for other_s in shifts_per_day:
                                if assignments.get((d, other_s)) == min_assigned_emp:
                                    already_working = True
                                    break
                            if already_working: continue
                            
                            # Execute Fairness Swap
                            assignments[(d, s)] = min_assigned_emp
                            fairness_counts[max_assigned_emp] -= 1
                            fairness_counts[min_assigned_emp] += 1
                            break
                        
            # Format for Database Document Structure
            dept_schedule = {d: {} for d in total_days}
            for (d, s), assigned_emp in assignments.items():
                dept_schedule[d][s] = assigned_emp
                
            final_schedule_db[dept] = dept_schedule
            final_fairness_db[dept] = fairness_counts
        else:
            # Fallback if CSP strictly fails to resolve
            final_schedule_db[dept] = {d: {} for d in total_days}
            final_fairness_db[dept] = {}
            print(f"Warning: Could not resolve strict CSP schedule for {dept}")

    # Saves to DB and includes the fairness score metrics array attached to the schedule doc
    save_schedule(role, final_schedule_db, final_fairness_db)
    return final_schedule_db, final_fairness_db
