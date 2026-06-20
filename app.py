import streamlit as st
import pandas as pd
from supabase import create_client, Client
from datetime import datetime

# ==========================================
# CLOUD DATABASE CONNECTION (SUPABASE)
# ==========================================

if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
else:
    URL = "https://lymbhtsaehqztqjlvgpb.supabase.co"
    KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx5bWJodHNhZWhxenRxamx2Z3BiIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODEzODA5MjUsImV4cCI6MjA5Njk1NjkyNX0.ZlzwBWeHmxHIhjXJwkRcCQZv8OnNhXQPxiMCDUCuNwk"

@st.cache_resource
def get_supabase_client() -> Client:
    return create_client(URL, KEY)

try:
    supabase: Client = get_supabase_client()
except Exception as e:
    st.error("🚨 Database Connection Error. Check your API Credentials.")
    st.stop()

# ==========================================
# SESSION STATE INITIALIZATION & ALERTS
# ==========================================
if "form_builders" not in st.session_state: st.session_state.form_builders = ""
if "form_notes" not in st.session_state: st.session_state.form_notes = ""
if "form_sequence" not in st.session_state: st.session_state.form_sequence = 1
if "form_panel_id" not in st.session_state: st.session_state.form_panel_id = 1

if "toast_msg" not in st.session_state: st.session_state.toast_msg = None
if "toast_icon" not in st.session_state: st.session_state.toast_icon = None

def clear_form_fields():
    st.session_state.form_builders = ""
    st.session_state.form_notes = ""
    st.session_state.form_sequence = 1
    st.session_state.form_panel_id = 1

if st.session_state.toast_msg:
    st.toast(st.session_state.toast_msg, icon=st.session_state.toast_icon)
    st.session_state.toast_msg = None
    st.session_state.toast_icon = None

# ==========================================
# DATA FETCHING FUNCTIONS
# ==========================================
def load_job_structures():
    try:
        response = supabase.table("job_configs").select("*").execute()
        rows = response.data
        
        if not rows:
            default_jobs = [
                {"job_id": "Job #68", "components": "Panel, Subpanel", "max_sequence": 10, "min_panel_id": 1, "max_panel_id": 45},
                {"job_id": "Job #61", "components": "Panel, Subpanel", "max_sequence": 5, "min_panel_id": 1, "max_panel_id": 45},
                {"job_id": "Job #100", "components": "Panel, Subpanel", "max_sequence": 16, "min_panel_id": 1, "max_panel_id": 45},
                {"job_id": "Job #18", "components": "Bottom, Top, Cap", "max_sequence": 8, "min_panel_id": 1, "max_panel_id": 8},
                {"job_id": "Job #12", "components": "Bottom, Top, Cap", "max_sequence": 8, "min_panel_id": 1, "max_panel_id": 8}
            ]
            supabase.table("job_configs").insert(default_jobs).execute()
            response = supabase.table("job_configs").select("*").execute()
            rows = response.data

        structure = {}
        for r in rows:
            structure[r["job_id"]] = {
                "components": [c.strip() for c in r["components"].split(",")],
                "max_sequence": int(r["max_sequence"]),
                "min_panel_id": int(r["min_panel_id"]),
                "max_panel_id": int(r["max_panel_id"])
            }
        return structure
    except Exception:
        return {}

JOB_STRUCTURES = load_job_structures()

# ==========================================
# STREAMLIT USER INTERFACE (UI)
# ==========================================
st.set_page_config(page_title="Cloud Panel Production Control", layout="wide")
st.title("🏭 Cloud Production Management System - Antenna Panels")

# Rediseñado a solo 3 pestañas para mejorar flujo CRUD unificado
tab_create, tab_read, tab_dashboard = st.tabs([
    "➕ Register / Setup Batches", 
    "🔍 Search, Update & Delete Logs", 
    "📊 Performance Dashboard"
])

# ------------------------------------------
# TAB 1: REGISTER PANELS & NEW JOBS (CREATE)
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
                
                max_seq = config["max_sequence"]
                if selected_component == "Top": max_seq = 4
                elif selected_component == "Cap": max_seq = 1
                    
                sequence = st.number_input(f"{selected_component} Number (1 to {max_seq}):", min_value=1, max_value=max_seq, value=st.session_state.form_sequence, key="input_seq")
                
                max_id = config["max_panel_id"]
                if selected_job in ["Job #18", "Job #12"] and selected_component == "Top": max_id = 4
                elif selected_job in ["Job #18", "Job #12"] and selected_component == "Cap": max_id = 1
                    
                panel_id = st.number_input(f"Panel ID ({config['min_panel_id']} to {max_id}):", min_value=int(config['min_panel_id']), max_value=int(max_id), value=st.session_state.form_panel_id, key="input_pid")

            with c2:
                prod_date = st.date_input("Production Date:", datetime.now())
                builders = st.text_input("Built By (Separate names with commas):", value=st.session_state.form_builders, placeholder="e.g., John Doe, Mark Smith", key="input_builders")
                notes = st.text_area("Production Notes / Logs:", value=st.session_state.form_notes, key="input_notes")

            if st.button("💾 Save Production Entry", type="primary"):
                if not builders.strip():
                    st.error("⚠️ The 'Built By' field is required.")
                else:
                    duplicate_check = supabase.table("panels").select("id")\
                        .eq("job_id", selected_job)\
                        .eq("component_type", selected_component)\
                        .eq("sequence_num", int(sequence))\
                        .eq("internal_panel_id", int(panel_id))\
                        .execute()
                    
                    if duplicate_check.data:
                        st.error(f"🚨 ERROR: A record for {selected_component} #{sequence} with Panel ID {panel_id} under {selected_job} already exists.")
                    else:
                        data_to_insert = {
                            "job_id": selected_job,
                            "component_type": selected_component,
                            "sequence_num": int(sequence),
                            "internal_panel_id": int(panel_id),
                            "production_date": str(prod_date),
                            "builders": builders.strip(),
                            "notes": notes.strip()
                        }
                        supabase.table("panels").insert(data_to_insert).execute()
                        
                        st.session_state.toast_msg = f"✔️ Registered {selected_component} #{sequence} for {selected_job}."
                        st.session_state.toast_icon = "🚀"
                        clear_form_fields()
                        st.rerun()

    with col_new_job:
        st.header("🛠️ Configure New Job Number")
        new_job_id = st.text_input("Job Name/Number:", placeholder="e.g., Job #75")
        structure_type = st.radio("Component Framework Layout:", ["Standard (Panel, Subpanel)", "Divided (Bottom, Top, Cap)", "Custom Layout"])
        
        if structure_type == "Standard (Panel, Subpanel)":
            suggested_comp, suggested_seq, suggested_max_id = "Panel, Subpanel", 10, 45
        elif structure_type == "Divided (Bottom, Top, Cap)":
            suggested_comp, suggested_seq, suggested_max_id = "Bottom, Top, Cap", 8, 8
        else:
            suggested_comp, suggested_seq, suggested_max_id = "Panel, Subpanel", 5, 45

        components_input = st.text_input("Components (Comma separated):", value=suggested_comp)
        max_seq_input = st.number_input("Maximum Component Sequence:", min_value=1, value=suggested_seq)
        
        nc1, nc2 = st.columns(2)
        with nc1: min_id_input = st.number_input("Minimum Panel ID:", min_value=1, value=1)
        with nc2: max_id_input = st.number_input("Maximum Panel ID:", min_value=1, value=suggested_max_id)
            
        if st.button("⚙️ Register Job Layout", use_container_width=True):
            if not new_job_id.strip() or not components_input.strip():
                st.error("⚠️ All metadata fields are mandatory.")
            elif new_job_id in JOB_STRUCTURES.keys():
                st.error("⚠️ This Job Number already exists.")
            else:
                job_data = {
                    "job_id": new_job_id.strip(),
                    "components": components_input.strip(),
                    "max_sequence": int(max_seq_input),
                    "min_panel_id": int(min_id_input),
                    "max_panel_id": int(max_id_input)
                }
                supabase.table("job_configs").insert(job_data).execute()
                st.session_state.toast_msg = f"✔️ '{new_job_id}' successfully added."
                st.session_state.toast_icon = "⚙️"
                st.rerun()

# ------------------------------------------
# TAB 2: SEARCH, UPDATE & DELETE LOGS (CRUD UNIFICADO)
# ------------------------------------------
with tab_read:
    st.header("Production Logs Management")
    st.caption("💡 Tip: Double-click any cell below to EDIT. To DELETE, click the left margin of a row and hit 'Delete' key or click the trash icon. Click 'Apply Changes' when done.")
    
    f_col1, f_col2, f_col3 = st.columns(3)
    with f_col1: filter_job = st.multiselect("Filter by Job:", list(JOB_STRUCTURES.keys()), key="f_job")
    with f_col2: filter_builder = st.text_input("Search Builder Name:", key="f_builder")
    with f_col3: filter_date = st.date_input("Filter from date:", value=None, key="f_date")

    cloud_query = supabase.table("panels").select("*")
    if filter_job: cloud_query = cloud_query.in_("job_id", filter_job)
    if filter_builder: cloud_query = cloud_query.ilike("builders", f"%{filter_builder}%")
    if filter_date: cloud_query = cloud_query.gte("production_date", str(filter_date))
    
    response = cloud_query.order("id", desc=True).execute()
    
    if response.data:
        df_origin = pd.DataFrame(response.data)
        
        # Mapeo estético de columnas visibles para el operador
        col_mapping = {
            "id": "Log ID", "job_id": "Job Number", "component_type": "Component Type",
            "sequence_num": "Sequence No", "internal_panel_id": "Panel ID",
            "production_date": "Date", "builders": "Builders", "notes": "Notes"
        }
        df_display = df_origin.rename(columns=col_mapping)
        
        # El Data Editor interactivo actúa como Excel con opción Update/Delete integrada
        edited_df = st.data_editor(
            df_display, 
            use_container_width=True, 
            hide_index=True,
            num_rows="dynamic", # Habilita la eliminación nativa de filas
            disabled=["Log ID"], # Bloquea la llave primaria ID para evitar daños
            key="production_editor"
        )
        
        # Procesar cambios cuando el usuario altera la tabla interactiva
        if st.button("💾 Apply Database Changes", type="primary"):
            # Detectar filas eliminadas comparando IDs
            original_ids = set(df_display["Log ID"].tolist())
            edited_ids = set(edited_df["Log ID"].tolist())
            deleted_ids = original_ids - edited_ids
            
            changes_detected = False
            
            # 1. Ejecutar Eliminaciones en Supabase
            if deleted_ids:
                for del_id in deleted_ids:
                    supabase.table("panels").delete().eq("id", int(del_id)).execute()
                st.session_state.toast_msg = f"🗑️ Successfully deleted {len(deleted_ids)} record(s)."
                st.session_state.toast_icon = "💥"
                changes_detected = True
            
            # 2. Ejecutar Actualizaciones (Updates) buscando discrepancias fila por fila
            # Invertimos el mapeo para devolver los datos al formato nativo de Supabase
            inv_mapping = {v: k for k, v in col_mapping.items()}
            df_edited_native = edited_df.rename(columns=inv_mapping)
            
            for _, row in df_edited_native.iterrows():
                row_id = int(row["id"])
                # Extraer la fila original correspondiente para comparar
                orig_row = df_origin[df_origin["id"] == row_id]
                
                if not orig_row.empty:
                    orig_row = orig_row.iloc[0]
                    # Si algo cambió en la fila, actualizamos
                    if not row.equals(orig_row):
                        # Evitar causar duplicados por mala edición
                        dup_mod = supabase.table("panels").select("id")\
                            .eq("job_id", row["job_id"])\
                            .eq("component_type", row["component_type"])\
                            .eq("sequence_num", int(row["sequence_num"]))\
                            .eq("internal_panel_id", int(row["internal_panel_id"]))\
                            .neq("id", row_id).execute()
                        
                        if dup_mod.data:
                            st.error(f"🚨 Cannot update Log ID {row_id}: This layout combination already exists.")
                            continue
                            
                        updated_fields = {
                            "job_id": row["job_id"], "component_type": row["component_type"], 
                            "sequence_num": int(row["sequence_num"]), "internal_panel_id": int(row["internal_panel_id"]), 
                            "production_date": str(row["production_date"]), "builders": str(row["builders"]), 
                            "notes": str(row["notes"])
                        }
                        supabase.table("panels").update(updated_fields).eq("id", row_id).execute()
                        changes_detected = True
                        st.session_state.toast_msg = "🔄 Production database logs successfully synchronized!"
                        st.session_state.toast_icon = "📝"
            
            if changes_detected:
                st.rerun()
            else:
                st.info("No modifications were detected to submit.")
                
        # Exportador CSV tradicional
        csv = edited_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Export Current View to CSV", data=csv, file_name="production_report.csv", mime="text/csv")
    else:
        st.warning("No production records match your cloud search criteria.")

# ------------------------------------------
# TAB 3: PERFORMANCE DASHBOARD (ANALYTICS)
# ------------------------------------------
with tab_dashboard:
    st.header("📈 Plant Performance Dashboard")
    res = supabase.table("panels").select("job_id, component_type, production_date, builders").execute()
    
    if res.data:
        df_metrics = pd.DataFrame(res.data)
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric("Total Components Manufactured", f"{len(df_metrics)} units")
        kpi2.metric("Active Jobs Logged", f"{df_metrics['job_id'].nunique()}")
        kpi3.metric("Last Dynamic Sync", datetime.now().strftime("%m/%d/%Y %I:%M %p"))
        
        st.markdown("---")
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            st.subheader("📦 Production Volume by Job Number")
            df_job_grp = df_metrics.groupby('job_id').size().reset_index(name='Units Produced')
            st.bar_chart(data=df_job_grp, x='job_id', y='Units Produced', use_container_width=True)
            
        with g_col2:
            st.subheader("📅 Daily Output Timeline")
            df_time_grp = df_metrics.groupby('production_date').size().reset_index(name='Output Count').sort_values(by='production_date')
            st.line_chart(data=df_time_grp, x='production_date', y='Output Count', use_container_width=True)
            
        st.markdown("---")
        st.subheader("👤 Shop Floor Output by Builder")
        builders_list = []
        for index, row in df_metrics.iterrows():
            names = [n.strip() for n in row['builders'].split(',') if n.strip()]
            for name in names: builders_list.append({'Employee': name, 'Units Logged': 1})
                
        df_builders_raw = pd.DataFrame(builders_list)
        if not df_builders_raw.empty:
            df_builders_final = df_builders_raw.groupby('Employee').sum().reset_index().sort_values(by='Units Logged', ascending=False)
            st.bar_chart(data=df_builders_final, x='Employee', y='Units Logged', use_container_width=True)
    else:
        st.info("The Dashboard metrics will automatically populate as soon as you record your first entries.")