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
    except Exception:
        st.error("❌ Invalid Username or Password/PIN.")

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

# Sidebar Operator Profile Box
st.sidebar.markdown(f"👤 **Operator:** `{st.session_state.display_username.upper()}`")
st.sidebar.markdown(f"🔑 **Role:** `{st.session_state.user_role.upper()}`")
if st.sidebar.button("Log Out", type="secondary", use_container_width=True):
    logout_user()

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
    # [Your core pre-existing business logic for adding panels goes here - translated to English]

with tab_read:
    st.header("Production History")
    # [Your core pre-existing business logic for searching, filtering, editing, deleting, and CSV export goes here]

with tab_dashboard:
    st.header("📈 Plant Performance Dashboard")
    # [Your core pre-existing analytics charts and metrics go here]

# ------------------------------------------
# TAB 4: USER CONTROL PANEL (ADMIN ONLY)
# ------------------------------------------
if st.session_state.user_role == "admin" and tab_admin_users:
    with tab_admin_users:
        st.header("⚙️ Shop Floor User Provisioning")
        st.write("As an Administrator, you can grant direct access credentials to new technical personnel and operators.")
        
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
                            # 1. Enmask the username into an email string for the Supabase Engine
                            masked_email = f"{cleaned_user}{INTERNAL_DOMAIN}"
                            
                            auth_res = supabase.auth.admin.create_user({
                                "email": masked_email,
                                "password": new_password,
                                "email_confirm": True
                            })
                            
                            if auth_res.user:
                                # 2. Insert the clean profile metadata into the public profiles table
                                profile_data = {
                                    "id": auth_res.user.id,
                                    "username": cleaned_user,
                                    "role": assigned_role
                                }
                                supabase.table("user_profiles").insert(profile_data).execute()
                                st.success(f"✔️ User '{cleaned_user}' successfully registered as {assigned_role.upper()}.")
                        except Exception:
                            st.error("🚨 Registration Error: Username already exists or higher system privileges are required.")
        
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