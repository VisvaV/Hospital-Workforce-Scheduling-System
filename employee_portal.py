import streamlit as st
import datetime
from database import get_personal_schedule, submit_leave_request, request_shift_swap, get_colleagues, db

def show_employee_portal(user):
    st.markdown(f"## Welcome, {user['name']}! 👋")
    st.markdown(f"**Role:** {user['role']} | **Department:** {user['department']}")
    
    tabs = st.tabs(["📅 Visual Schedule", "🏖️ Request Leave", "🔄 Shift Swap"])
    
    my_schedule = get_personal_schedule(user['name'])
    
    # Pre-fetch approved leaves for 🏖️ badging
    leaves = list(db["requests"].find({"id": user["id"], "Status": "Approved"}))
    approved_leave_days = set()
    for l in leaves:
        for date_str in l["Dates"]:
            try:
                d_name = datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
            except ValueError:
                d_name = date_str
            approved_leave_days.add(d_name)
    
    with tabs[0]:
        st.subheader("Your Weekly Calendar")
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        
        # Build 7-day grid using columns
        cols = st.columns(7)
        total_shifts = 0
        busiest_day = ("None", 0)
        shift_counts_by_day = {d: 0 for d in days}
        
        for i, day in enumerate(days):
            with cols[i]:
                st.markdown(f"<div style='text-align: center; font-weight: bold; padding: 5px; color: #66fcf1; border-bottom: 1px solid #45a29e;'>{day[:3]}</div>", unsafe_allow_html=True)
                
                day_shifts = my_schedule.get(day, [])
                shift_counts_by_day[day] = len(day_shifts)
                total_shifts += len(day_shifts)
                
                badge = " 🏖️" if day in approved_leave_days else ""
                
                if day_shifts:
                    for s in day_shifts:
                        st.markdown(f"""
                        <div style='background-color: #1f2833; border: 1px solid #45a29e; border-radius: 5px; padding: 10px; margin-top: 10px; font-size: 12px; text-align: center;'>
                            <b>{s.split('(')[0].strip()}</b><br>
                            <span style='color: #c5c6c7;'>{s.split('(')[1].strip()[:-1]}</span>{badge}
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    if badge:
                        st.markdown(f"""
                        <div style='background-color: transparent; border: 1px dashed #45a29e; border-radius: 5px; padding: 10px; margin-top: 10px; font-size: 12px; text-align: center; color: gray;'>
                            OFF {badge}
                        </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='min-height: 50px;'></div>", unsafe_allow_html=True)
                        
        for d, count in shift_counts_by_day.items():
            if count > busiest_day[1]:
                busiest_day = (d, count)
                
        # Get dept average for fairness score
        all_schedules = db["schedules"].find_one({"role": user["role"], "department": user["department"]})
        dept_avg = 0
        if all_schedules and "fairness_scores" in all_schedules:
            scores = all_schedules["fairness_scores"].values()
            if scores:
                dept_avg = round(sum(scores) / len(scores), 1)
        
        st.markdown("---")
        st.subheader("📊 Shift Summary")
        mcol1, mcol2, mcol3 = st.columns(3)
        mcol1.metric("Total Shifts this Week", total_shifts)
        mcol2.metric("Busiest Day", busiest_day[0], f"{busiest_day[1]} shifts")
        mcol3.metric("Fairness Score", f"{total_shifts} vs {dept_avg} (Dept Avg)", 
                     delta=round(total_shifts - dept_avg, 1), 
                     delta_color="inverse")
            
    with tabs[1]:
        st.subheader("Request Time Off")
        with st.form("leave_form"):
            selected_date = st.date_input("Select Date", min_value=datetime.date.today())
            duration = st.selectbox("Duration", ["1 Day", "2 Days", "3 Days"])
            
            submitted = st.form_submit_button("Submit Leave Request")
            if submitted:
                success = submit_leave_request(
                    user_id=user["id"],
                    name=user["name"],
                    department=user["department"],
                    request_date=selected_date.strftime("%Y-%m-%d"),
                    duration=duration
                )
                if success:
                    st.success("Leave Request Submitted! It is pending admin approval and conflict review.")
                else:
                    st.error("You already have a request submitted for this target date.")
                    
    with tabs[2]:
        st.subheader("🔄 Request Shift Swap")
        
        # Extract individual shifts
        available_shifts = []
        for day, shifts in my_schedule.items():
            for s in shifts:
                shift_name = s.split("(")[0].strip()
                available_shifts.append(f"{day} - {shift_name}")
                
        colleagues = [c["name"] for c in get_colleagues(user["department"], user["role"]) if c["id"] != user["id"]]
        
        with st.form("swap_form"):
            if not available_shifts:
                st.info("You don't have any assigned shifts to swap!")
                st.form_submit_button("Submit Swap Request", disabled=True)
            else:
                target_shift = st.selectbox("Select your shift to swap out", available_shifts)
                target_colleague = st.selectbox("Select Colleague to swap with", colleagues)
                
                submitted = st.form_submit_button("Submit Swap Request")
                if submitted:
                    shift_day = target_shift.split(" - ")[0]
                    shift_num = target_shift.split(" - ")[1]
                    
                    request_shift_swap(
                        requester_id=user["id"],
                        target_name=target_colleague,
                        shift_date=shift_day,
                        shift_num=shift_num
                    )
                    st.success(f"Swap request sent involving {target_colleague}. Pending Admin approval.")
