import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# ==========================================
# CONFIGURATION & DATABASE SETUP
# ==========================================
DB_NAME = "antenna_production.db"

def init_db():
    """Initializes the database and creates the tables if they don't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Job Configurations Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS job_configs (
            job_id TEXT PRIMARY KEY,
            components TEXT NOT NULL,
            max_sequence INTEGER NOT NULL,
            min_panel_id INTEGER NOT NULL,
            max_panel_id INTEGER NOT NULL
        )
    ''')
    
    # Populate default jobs if the table is empty
    cursor.execute("SELECT COUNT(*) FROM job_configs")
    if cursor.fetchone()[0] == 0:
        default_jobs = [
            ("Job #68", "Panel, Subpanel", 10, 1, 45),
            ("Job #61", "Panel, Subpanel", 5, 1, 45),
            ("Job #100", "Panel, Subpanel", 16, 1, 45),
            ("Job #18", "Bottom, Top, Cap", 8, 1, 8),
            ("Job #12", "Bottom, Top, Cap", 8, 1, 8)
        ]
        cursor.executemany('''
            INSERT INTO job_configs (job_id, components, max_sequence, min_panel_id, max_panel_id)
            VALUES (?, ?, ?, ?, ?)
        ''', default_jobs)
    
    # 2. Panels Production Table (Core CRUD)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            component_type TEXT NOT NULL,
            sequence_num INTEGER NOT NULL,
            internal_panel_id INTEGER NOT NULL,
            production_date TEXT NOT NULL,
            builders TEXT NOT NULL,
            notes TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Initialize Database Schema
init_db()

def load_job_structures():
    """Dynamically loads job configurations from the DB."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT job_id, components, max_sequence, min_panel_id, max_panel_id FROM job_configs")
    rows = cursor.fetchall()
    conn.close()
    
    structure = {}
    for r in rows:
        structure[r[0]] = {
            "components": [c.strip() for c in r[1].split(",")],
            "max_sequence": r[2],
            "min_panel_id": r[3],
            "max_panel_id": r[4]
        }
    return structure

# Load dynamic structure
JOB_STRUCTURES = load_job_structures()

# ==========================================
# STREAMLIT USER INTERFACE
# ==========================================
st.set_page_config(page_title="Panel Production Control", layout="wide")
st.title("🏭 Production Management System - Antenna Panels")

# Application Tabs (CRUD + Analytics)
tab_create, tab_read, tab_dashboard, tab_update_delete = st.tabs([
    "➕ Register / Setup Batches", 
    "🔍 Search & Logs (Read)", 
    "📊 Performance Dashboard",
    "⚙️ Modify / Delete (Update/Delete)"
])

# ------------------------------------------
# TAB 1: REGISTER PANELES & NEW JOBS (CREATE)
# ------------------------------------------
with tab_create:
    col_log, col_new_job = st.columns([1.4, 0.9])
    
    with col_log:
        st.header("Log New Panel / Component")
        if JOB_STRUCTURES:
            c1, c2 = st.columns(2)
            with c1:
                selected_job = st.selectbox("Select Job Number:", list(JOB_STRUCTURES.keys()), key="add_job")
                config = JOB_STRUCTURES[selected_job]
                selected_component = st.selectbox("Component Type:", config["components"], key="add_comp")
                
                # Special embedded business rules for Top/Cap components
                max_seq = config["max_sequence"]
                if selected_component == "Top": max_seq = 4
                elif selected_component == "Cap": max_seq = 1
                    
                sequence = st.number_input(f"{selected_component} Number (1 to {max_seq}):", min_value=1, max_value=max_seq, value=1)
                
                max_id = config["max_panel_id"]
                if selected_job in ["Job #18", "Job #12"] and selected_component == "Top": max_id = 4
                elif selected_job in ["Job #18", "Job #12"] and selected_component == "Cap": max_id = 1
                    
                panel_id = st.number_input(f"Panel ID ({config['min_panel_id']} to {max_id}):", min_value=int(config['min_panel_id']), max_value=int(max_id), value=1)

            with c2:
                prod_date = st.date_input("Production Date:", datetime.now())
                builders = st.text_input("Built By (Separate names with commas):", placeholder="e.g., John Doe, Mark Smith")
                notes = st.text_area("Production Notes / Logs:")

            if st.button("💾 Save Production Entry", type="primary"):
                if not builders.strip():
                    st.error("⚠️ The 'Built By' field is required.")
                else:
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO panels (job_id, component_type, sequence_num, internal_panel_id, production_date, builders, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (selected_job, selected_component, sequence, panel_id, str(prod_date), builders, notes))
                    conn.commit()
                    conn.close()
                    st.success(f"✔️ Success! Registered {selected_component} #{sequence} for {selected_job}.")
                    st.rerun()
        else:
            st.warning("No job configurations found in the system.")

    with col_new_job:
        st.header("🛠️ Configure New Job Number")
        st.caption("Create a new custom run with its own validations and components.")
        
        new_job_id = st.text_input("Job Name/Number:", placeholder="e.g., Job #75")
        structure_type = st.radio("Component Framework Layout:", ["Standard (Panel, Subpanel)", "Divided (Bottom, Top, Cap)", "Custom Layout"])
        
        if structure_type == "Standard (Panel, Subpanel)":
            suggested_comp = "Panel, Subpanel"
            suggested_seq = 10
            suggested_max_id = 45
        elif structure_type == "Divided (Bottom, Top, Cap)":
            suggested_comp = "Bottom, Top, Cap"
            suggested_seq = 8
            suggested_max_id = 8
        else:
            suggested_comp = "Panel, Subpanel"
            suggested_seq = 5
            suggested_max_id = 45

        components_input = st.text_input("Components (Comma separated):", value=suggested_comp)
        max_seq_input = st.number_input("Maximum Component Sequence:", min_value=1, value=suggested_seq)
        
        nc1, nc2 = st.columns(2)
        with nc1:
            min_id_input = st.number_input("Minimum Panel ID:", min_value=1, value=1)
        with nc2:
            max_id_input = st.number_input("Maximum Panel ID:", min_value=1, value=suggested_max_id)
            
        if st.button("⚙️ Register Job Layout", use_container_width=True):
            if not new_job_id.strip() or not components_input.strip():
                st.error("⚠️ Job name and components are mandatory fields.")
            elif new_job_id in JOB_STRUCTURES.keys():
                st.error("⚠️ This Job Number already exists in the system database.")
            else:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO job_configs (job_id, components, max_sequence, min_panel_id, max_panel_id)
                    VALUES (?, ?, ?, ?, ?)
                ''', (new_job_id.strip(), components_input.strip(), max_seq_input, min_id_input, max_id_input))
                conn.commit()
                conn.close()
                st.success(f"✔️ '{new_job_id}' successfully added to production presets.")
                st.rerun()

# ------------------------------------------
# TAB 2: SEARCH & LOGS (READ)
# ------------------------------------------
with tab_read:
    st.header("Production Filters & Queries")
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1: filter_job = st.multiselect("Filter by Job:", list(JOB_STRUCTURES.keys()))
    with f_col2: filter_builder = st.text_input("Search by Builder Name:")
    with f_col3: filter_date = st.date_input("Filter from date:", value=None)

    query = "SELECT id as 'Log ID', job_id as 'Job Number', component_type as 'Component Type', sequence_num as 'Sequence No', internal_panel_id as 'Panel ID', production_date as 'Date', builders as 'Builders', notes as 'Notes' FROM panels WHERE 1=1"
    params = []
    
    if filter_job:
        query += f" AND job_id IN ({','.join(['?']*len(filter_job))})"
        params.extend(filter_job)
    if filter_builder:
        query += " AND builders LIKE ?"
        params.append(f"%{filter_builder}%")
    if filter_date:
        query += " AND production_date >= ?"
        params.append(str(filter_date))
        
    query += " ORDER BY id DESC"

    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Selection to CSV", data=csv, file_name="production_report.csv", mime="text/csv")
    else:
        st.warning("No production records match your search criteria.")

# ------------------------------------------
# TAB 3: PERFORMANCE DASHBOARD (ANALYTICS)
# ------------------------------------------
with tab_dashboard:
    st.header("📈 Plant Performance Dashboard")
    
    conn = sqlite3.connect(DB_NAME)
    df_metrics = pd.read_sql_query("SELECT job_id, component_type, production_date, builders FROM panels", conn)
    conn.close()
    
    if not df_metrics.empty:
        total_units = len(df_metrics)
        active_jobs = df_metrics['job_id'].nunique()
        
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Components Manufactured", f"{total_units} units")
        kpi2.metric("Active Jobs Logged", f"{active_jobs}")
        kpi3.metric("Last Dynamic Sync", datetime.now().strftime("%m/%d/%Y %I:%M %p"))
        
        st.markdown("---")
        
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.subheader("📦 Production Volume by Job Number")
            df_job_grp = df_metrics.groupby('job_id').size().reset_index(name='Units Produced')
            st.bar_chart(data=df_job_grp, x='job_id', y='Units Produced', use_container_width=True)
            
        with g_col2:
            st.subheader("📅 Daily Output Timeline")
            df_time_grp = df_metrics.groupby('production_date').size().reset_index(name='Output Count')
            df_time_grp = df_time_grp.sort_values(by='production_date')
            st.line_chart(data=df_time_grp, x='production_date', y='Output Count', use_container_width=True)
            
        st.markdown("---")
        st.subheader("👤 Shop Floor Output by Builder")
        
        builders_list = []
        for index, row in df_metrics.iterrows():
            names = [n.strip() for n in row['builders'].split(',') if n.strip()]
            for name in names:
                builders_list.append({'Employee': name, 'Units Logged': 1})
                
        df_builders_raw = pd.DataFrame(builders_list)
        if not df_builders_raw.empty:
            df_builders_final = df_builders_raw.groupby('Employee').sum().reset_index()
            df_builders_final = df_builders_final.sort_values(by='Units Logged', ascending=False)
            st.bar_chart(data=df_builders_final, x='Employee', y='Units Logged', use_container_width=True)
    else:
        st.info("The Dashboard metrics will automatically populate as soon as you record your first entries.")

# ------------------------------------------
# TAB 4: MODIFY / DELETE (UPDATE/DELETE)
# ------------------------------------------
with tab_update_delete:
    st.header("Modify or Remove Production Records")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, job_id, component_type, sequence_num FROM panels ORDER BY id DESC")
    record_list = cursor.fetchall()
    conn.close()
    
    if record_list:
        record_options = {r[0]: f"Log ID: {r[0]} | {r[1]} - {r[2]} #{r[3]}" for r in record_list}
        id_to_modify = st.selectbox("Select Target Record to Update/Delete:", list(record_options.keys()), format_func=lambda x: record_options[x])
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT job_id, component_type, sequence_num, internal_panel_id, production_date, builders, notes FROM panels WHERE id = ?", (id_to_modify,))
        current_data = cursor.fetchone()
        conn.close()
        
        if current_data:
            st.markdown("---")
            u_col1, u_col2 = st.columns(2)
            with u_col1:
                u_job = st.selectbox("Job Number:", list(JOB_STRUCTURES.keys()), index=list(JOB_STRUCTURES.keys()).index(current_data[0]) if current_data[0] in JOB_STRUCTURES else 0, key="u_jr")
                u_config = JOB_STRUCTURES[u_job] if u_job in JOB_STRUCTURES else {"components": [current_data[1]]}
                idx_comp = u_config["components"].index(current_data[1]) if current_data[1] in u_config["components"] else 0
                u_component = st.selectbox("Component Type:", u_config["components"], index=idx_comp, key="u_cr")
                u_sequence = st.number_input("Sequence Number:", min_value=1, value=int(current_data[2]), key="u_sr")
                u_panel_id = st.number_input("Internal Panel ID:", min_value=1, value=int(current_data[3]), key="u_pr")
                
            with u_col2:
                u_date = st.date_input("Date:", value=datetime.strptime(current_data[4], "%Y-%m-%d"), key="u_dr")
                u_builders = st.text_input("Builders:", value=current_data[5], key="u_br")
                u_notes = st.text_area("Notes:", value=current_data[6], key="u_nr")
            
            btn_col1, btn_col2, _ = st.columns([1, 1, 2])
            with btn_col1:
                if st.button("🔄 Update Record", type="secondary", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE panels SET job_id=?, component_type=?, sequence_num=?, internal_panel_id=?, production_date=?, builders=?, notes=? WHERE id=?
                    ''', (u_job, u_component, u_sequence, u_panel_id, str(u_date), u_builders, u_notes, id_to_modify))
                    conn.commit()
                    conn.close()
                    st.success("Record updated successfully!")
                    st.rerun()
                    
            with btn_col2:
                if st.button("🗑️ Delete Record", type="primary", use_container_width=True):
                    conn = sqlite3.connect(DB_NAME)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM panels WHERE id=?", (id_to_modify,))
                    conn.commit()
                    conn.close()
                    st.warning(f"Record #{id_to_modify} has been permanently deleted.")
                    st.rerun()
    else:
        st.info("No logs currently available for modification.")