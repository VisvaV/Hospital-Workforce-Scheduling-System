import streamlit as st
from database import authenticate_user
from admin_dashboard import show_admin_dashboard
from employee_portal import show_employee_portal

st.set_page_config(page_title="HWSMS System", page_icon="🏥", layout="wide")

# Futuristic Minimal CSS
CSS = """
<style>
/* Base dark mode and typography */
body, .stApp {
    background-color: #0b0c10;
    color: #c5c6c7;
    font-family: 'Inter', sans-serif;
}
/* Headings */
h1, h2, h3 {
    color: #66fcf1;
    font-weight: 600;
}
/* Cards / Expanders */
div[data-testid="stExpander"] {
    background-color: #1f2833;
    border: 1px solid #45a29e;
    border-radius: 8px;
    padding: 10px;
}
/* Buttons */
.stButton>button {
    background-color: #45a29e;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 10px 24px;
    transition: 0.3s;
}
.stButton>button:hover {
    background-color: #66fcf1;
    color: #0b0c10;
    box-shadow: 0 0 10px #66fcf1;
}
/* Dataframes */
div[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

if "user" not in st.session_state:
    st.session_state["user"] = None

def main():
    if not st.session_state["user"]:
        st.markdown("<div style='text-align: center;'><h1>Hospital Workforce System</h1><p>Futuristic Scheduling driven by CSP</p></div><br><br>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        
        with col2:
            st.markdown("### Log In")
            with st.form('login_form'):
                name = st.text_input("Name (e.g., Admin1, Dr. Visva)")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Verify", use_container_width=True)
                
                if submit:
                    user = authenticate_user(name, password)
                    if user:
                        st.session_state["user"] = user
                        st.rerun()
                    else:
                        st.error("Invalid credentials!")
    else:
        user = st.session_state["user"]
        
        # Sidebar with simple logout
        with st.sidebar:
            st.write(f"**Logged in as:** {user['name']}")
            st.divider()
            if st.button("Logout"):
                st.session_state["user"] = None
                st.rerun()
                
        # Route to proper dashboard
        if user["role"] == "Admin":
            show_admin_dashboard()
        else:
            show_employee_portal(user)

if __name__ == "__main__":
    main()
