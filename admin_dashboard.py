import streamlit as st
import pandas as pd
from database import get_pending_requests, update_request_status, get_schedule, get_pending_swaps, approve_swap, get_analytics_data, db
from scheduler import generate_schedule

def show_admin_dashboard():
    st.markdown("## 🏥 Command Center Admin Dashboard")
    
    tabs = st.tabs(["📅 Full Schedule", "📋 Leave Requests", "🔄 Swap Requests", "📊 Analytics"])
    
    with tabs[0]:
        st.subheader("Master Calendar Schedule")
        
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Generate Docs Schedule", use_container_width=True):
                with st.spinner("Calculating CSP paths..."):
                    generate_schedule("Doctor")
                st.rerun()
        with c2:
            if st.button("Generate Nurses Schedule", use_container_width=True):
                with st.spinner("Calculating CSP paths..."):
                    generate_schedule("Nurse")
                st.rerun()
                
        st.markdown("---")
        role_view = st.selectbox("Select Role to Render", ["Doctor", "Nurse"])
        schedule_data = get_schedule(role_view) # dict mapping Dept -> {schedule: {}, fairness_scores: {}}
        
        if schedule_data:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            
            # Fetch all approved leaves for badging
            approved_reqs = list(db["requests"].find({"Status": "Approved"}))
            leave_map = {}
            for req in approved_reqs:
                emp_name = req["Name"]
                for date_str in req["Dates"]:
                    # map down to day for dummy mapping
                    import datetime
                    try:
                        d_name = datetime.datetime.strptime(date_str, "%Y-%m-%d").strftime("%A")
                    except ValueError:
                        d_name = date_str
                    if emp_name not in leave_map:
                        leave_map[emp_name] = []
                    leave_map[emp_name].append(d_name)
                    
            # Render HTML Tables per department
            colors = ["#1f2833", "#232b2b", "#0b0c10"] # minimal palette
            html_out = ""
            for i, (dept, data) in enumerate(schedule_data.items()):
                sch = data.get("schedule", {})
                bg = colors[i % len(colors)]
                
                html_out += f"<h4 style='color: #66fcf1;'>{dept} Department</h4>"
                html_out += f"<table style='width: 100%; text-align: left; background-color: {bg}; border-collapse: collapse; margin-bottom: 20px; font-size: 14px; border: 1px solid #45a29e;'>"
                
                # Headers
                html_out += "<tr>"
                for d in days:
                    html_out += f"<th style='padding: 10px; border-bottom: 1px solid #45a29e;'>{d}</th>"
                html_out += "</tr>"
                
                # Shift 1
                html_out += "<tr>"
                for d in days:
                    emp = sch.get(d, {}).get("Shift 1", "-")
                    # Check if on leave
                    is_leave = False
                    if emp != "-" and d in leave_map.get(emp, []):
                        is_leave = True
                    display = f"<del>{emp}</del> 🏖️" if is_leave else emp
                    html_out += f"<td style='padding: 10px; border-right: 1px solid #45a29e;'><b>S1:</b> <br>{display}</td>"
                html_out += "</tr>"
                
                # Shift 2
                html_out += "<tr>"
                for d in days:
                    emp = sch.get(d, {}).get("Shift 2", "-")
                    is_leave = False
                    if emp != "-" and d in leave_map.get(emp, []):
                        is_leave = True
                    display = f"<del>{emp}</del> 🏖️" if is_leave else emp
                    html_out += f"<td style='padding: 10px; border-right: 1px solid #45a29e;'><b>S2:</b> <br>{display}</td>"
                html_out += "</tr>"
                
                html_out += "</table>"
            
            st.markdown(html_out, unsafe_allow_html=True)
            
        else:
            st.warning("No Master Schedule Rendered.")

    with tabs[1]:
        st.subheader("Active Leave Requests")
        requests = get_pending_requests()
        
        if not requests:
            st.info("Inbox Zero! No pending leave requests.")
        else:
            for req in requests:
                dates_str = ", ".join(req["Dates"])
                conflict_status = req.get("has_conflict", False)
                conflict_msg = req.get("conflict_reason", "Unknown")
                
                warning_color = "#ff4b4b" if conflict_status else "#4caf50"
                
                with st.expander(f"Request: {req['Name']} - {req['Dept']} ({dates_str})"):
                    st.markdown(f"**Duration:** {req.get('Duration', 'N/A')}")
                    st.markdown(f"**Conflict Warning:** <span style='color: {warning_color}; font-weight: bold;'>{conflict_msg}</span>", unsafe_allow_html=True)
                    
                    st.markdown("**(Replacement engine executes natively upon approval)**")
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("Approve & Automate Swap", key=f"app_{req['_id']}", type="primary"):
                            update_request_status(req["_id"], "accept", req["Dates"])
                            st.rerun()
                    with c2:
                        if st.button("Deny Request", key=f"den_{req['_id']}"):
                            update_request_status(req["_id"], "deny", req["Dates"])
                            st.rerun()

    with tabs[2]:
        st.subheader("Shift Swap Queue")
        swaps = get_pending_swaps()
        
        if not swaps:
            st.info("No swap requests found.")
        else:
            for swp in swaps:
                with st.container():
                    st.markdown(f"""
                    <div style='background-color: #1f2833; padding: 15px; border-radius: 8px; border-left: 5px solid #66fcf1; margin-bottom: 10px;'>
                        <h4>{swp['requester_name']} ➔ wants to swap {swp['shift_date']} ({swp['shift_num']})</h4>
                        <b>Target Colleague:</b> {swp['target_name']}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("Approve Swap Override", key=f"swap_{swp['_id']}", type="primary"):
                        success = approve_swap(swp["_id"], override=True)
                        if success:
                            st.success("Swap applied directly to Master Schedule.")
                        else:
                            st.error("Swap invalid context.")
                        import time
                        time.sleep(1.5)
                        st.rerun()

    with tabs[3]:
        st.subheader("Operational Analytics")
        data = get_analytics_data()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Shift Distribution (Fairness Check)")
            if data["shift_distribution"]:
                df_shifts = pd.DataFrame(list(data["shift_distribution"].items()), columns=["Employee", "Total Shifts"])
                st.bar_chart(data=df_shifts, x="Employee", y="Total Shifts")
            else:
                st.caption("No schedule data generated yet.")
                
        with col2:
            st.markdown("#### Leave Frequency by Department")
            if data["leave_frequency"]:
                df_leaves = pd.DataFrame(list(data["leave_frequency"].items()), columns=["Department", "Leaves Requested"])
                st.bar_chart(data=df_leaves, x="Department", y="Leaves Requested")
            else:
                st.caption("No leave requests found.")
                
        st.divider()
        st.markdown("#### Department Coverage Heatmap")
        st.markdown("Shows how many distinct shifts exist out of optimal load per department per day.")
        
        if data["coverage"]:
            # Heat map logic - rendered simply using styling dataframe
            df_cov = pd.DataFrame(data["coverage"]).fillna(0)
            
            # Apply styling
            def color_intensity(val):
                color = '#ff4b4b' if val == 0 else '#faca2b' if val == 1 else '#4caf50'
                return f'background-color: {color}; color: black'
                
            st.dataframe(df_cov.style.map(color_intensity), use_container_width=True)
        else:
            st.warning("Coverage matrix offline.")
