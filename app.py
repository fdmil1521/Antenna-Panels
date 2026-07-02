import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# DATABASE CONNECTION & CONFIGURATION
# ==========================================
URL = st.secrets["SUPABASE_URL"]
KEY = st.secrets["SUPABASE_KEY"]

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(URL, KEY)

supabase: Client = get_supabase_client()

# Internal domain mask to satisfy Supabase Auth requirements invisibly
INTERNAL_DOMAIN = "@factory.local"

# ==========================================
# AUTHENTICATION SESSION STATE
# ==========================================
if "auth_user" not in st.session_state: st.session_state.auth_user = None
if "user_role" not in st.session_state: st.session_state.user_role = None
if "display_username" not in st.session_state: st.session_state.display_username = ""

def login_user(username, password):
    # Invisibly mask the plant username as a valid email format for Supabase
    fictional_email = f"{username.lower().strip()}{INTERNAL_DOMAIN}"
    try:
        auth_response = supabase.auth.sign_in_with_password({"email": fictional_email, "password": password})
        if auth_response.user:
            st.session_state.auth_user = auth_response.user
            
            # Fetch username and assigned role from public user profiles table
            profile_response = supabase.table("user_profiles").select("username, role").eq("id", auth_response.user.id).execute()
            if profile_response.data:
                st.session_state.user_role = profile_response.data[0]["role"]
                st.session_state.display_username = profile_response.data[0]["username"]
            else:
                st.session_state.user_role = "operator"
                st.session_state.display_username = username
            
            st.rerun()
    except Exception as e:
        st.error(f"❌ Invalid Username or Password/PIN. API Details: {str(e)}")

def logout_user():
    try:
        supabase.auth.sign_out()
    except:
        pass
    st.session_state.auth_user = None
    st.session_state.user_role = None
    st.session_state.display_username = ""
    st.rerun()

# ==========================================
# LOGIN SCREEN INTERFACE
# ==========================================
if st.session_state.auth_user is None:
    st.markdown("<h2 style='text-align: center;'>🏭 Production Control System - Shop Floor</h2>", unsafe_allow_html=True)
    
    # Center the login form for tablets and desktops
    _, col_login, _ = st.columns([0.6, 1, 0.6])
    with col_login:
        with st.form("login_form"):
            st.markdown("### Sign In")
            user_input = st.text_input("Username / Operator ID:", placeholder="e.g., operator1 or employee ID")
            password_input = st.text_input("Password / PIN:", type="password")
            submit_login = st.form_submit_button("Enter System", use_container_width=True)
            
            if submit_login:
                if user_input.strip() and password_input.strip():
                    login_user(user_input.strip(), password_input.strip())
                else:
                    st.warning("⚠️ Please fill in both fields.")
    st.stop()

# ==========================================
# MAIN APPLICATION INTERFACE (AUTHENTICATED)
# ==========================================

# Sidebar Operator Profile Box (Safe handling to avoid NoneType upper() crashes)
op_name = str(st.session_state.display_username).upper() if st.session_state.display_username else "UNKNOWN"
op_role = str(st.session_state.user_role).upper() if st.session_state.user_role else "OPERATOR"

st.sidebar.markdown(f"👤 **Operator:** `{op_name}`")
st.sidebar.markdown(f"🔑 **Role:** `{op_role}`")
if st.sidebar.button("Log Out", type="secondary", use_container_width=True):
    logout_user()

# ==========================================
# LIVE DATA DIAGNOSTIC (TEMPORAL)
# ==========================================
st.sidebar.markdown("---")
st.sidebar.subheader("🔍 DB Diagnostic Check")
try:
    test_panels = supabase.table("panels").select("*").limit(5).execute()
    test_jobs = supabase.table("job_configs").select("*").limit(5).execute()
    st.sidebar.success(f"📦 Panels rows read: {len(test_panels.data)}")
    st.sidebar.success(f"⚙️ Job Configs rows read: {len(test_jobs.data)}")
except Exception as db_err:
    st.sidebar.error(f"🚨 Query Failed: {str(db_err)}")

# Dynamic Menu Tabs based on Role Access
if st.session_state.user_role == "admin":
    tab_create, tab_read, tab_dashboard, tab_admin_users = st.tabs([
        "➕ Register / Setup Batches", 
        "🔍 Search & Manage Logs", 
        "📊 Performance Dashboard",
        "⚙️ Admin: User Permissions & Floor Profiles"
    ])
else:
    tab_create, tab_read, tab_dashboard = st.tabs([
        "➕ Register / Setup Batches", 
        "🔍 Search & Manage Logs", 
        "📊 Performance Dashboard"
    ])
    tab_admin_users = None

# ------------------------------------------
# TAB 1: REGISTER PANELS & NEW JOBS
# ------------------------------------------
with tab_create:
    st.header("Log New Panel / Component")
    st.write("Welcome to the registration area.")
    # [Tus formularios para insertar datos en st.session_state o consultas a panels/job_configs van aquí abajo]

# ------------------------------------------
# TAB 2: HISTORY READ
# ------------------------------------------
with tab_read:
    st.header("Production History")
    st.write("Use the controls below to search or modify data.")
    
    # Ejemplo de visualización directa para comprobar la lectura
    st.subheader("Live Panels Data View")
    try:
        all_panels = supabase.table("panels").select("*").execute()
        if all_panels.data:
            st.dataframe(pd.DataFrame(all_panels.data), use_container_width=True)
        else:
            st.info("No data returned from the 'panels' table.")
    except Exception as read_err:
        st.error(f"Could not load historical panel dataframe: {str(read_err)}")

# ------------------------------------------
# TAB 3: DASHBOARD
# ------------------------------------------
with tab_dashboard:
    st.header("📈 Plant Performance Dashboard")
    st.write("Real-time factory metrics.")

# ------------------------------------------
# TAB 4: USER CONTROL PANEL (ADMIN ONLY)
# ------------------------------------------
if st.session_state.user_role == "admin" and tab_admin_users:
    with tab_admin_users:
        st.header("⚙️ Shop Floor User Provisioning")
        st.write("As an Administrator, you can grant direct access credentials to new technical personnel.")
        
        col_new_u, col_list_u = st.columns([1.2, 1])
        
        with col_new_u:
            st.subheader("Register New Personnel")
            with st.form("register_user_form", clear_on_submit=True):
                new_username = st.text_input("Define Shop Floor Username/ID:", placeholder="e.g., john.doe")
                new_password = st.text_input("Access Password / PIN (min. 6 characters):", type="password")
                assigned_role = st.selectbox("Authorization Level:", ["operator", "admin"])
                
                submit_registration = st.form_submit_button("Create Plant Account", type="primary")
                
                if submit_registration:
                    cleaned_user = new_username.strip().lower()
                    if not cleaned_user or len(new_password) < 6:
                        st.error("⚠️ Username is mandatory and Password/PIN must be at least 6 characters long.")
                    else:
                        try:
                            masked_email = f"{cleaned_user}{INTERNAL_DOMAIN}"
                            auth_res = supabase.auth.admin.create_user({
                                "email": masked_email,
                                "password": new_password,
                                "email_confirm": True
                            })
                            if auth_res.user:
                                profile_data = {
                                    "id": auth_res.user.id,
                                    "username": cleaned_user,
                                    "role": assigned_role
                                }
                                supabase.table("user_profiles").insert(profile_data).execute()
                                st.success(f"✔️ User '{cleaned_user}' successfully registered as {assigned_role.upper()}.")
                        except Exception as reg_err:
                            st.error(f"🚨 Registration Error: {str(reg_err)}")
        
        with col_list_u:
            st.subheader("Authorized Personnel Directory")
            try:
                users_profiles_res = supabase.table("user_profiles").select("username, role, created_at").execute()
                if users_profiles_res.data:
                    df_users = pd.DataFrame(users_profiles_res.data)
                    df_users.columns = ["Username / ID", "Access Role", "Registration Date"]
                    st.dataframe(df_users, use_container_width=True, hide_index=True)
                else:
                    st.info("No operator profiles found in the system database.")
            except Exception:
                st.warning("Could not fetch the active operator directory at this time.")