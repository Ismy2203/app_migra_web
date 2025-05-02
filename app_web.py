import streamlit as st
import pandas as pd
import io
from services.odoo_connection import OdooConnection
from services.export_service import export_model_data
from services.import_service import import_records
from utils.logger import setup_logger, log_message

setup_logger()

st.set_page_config(page_title="Data Migration Tool", layout="wide")
st.title("🔁 Odoo Data Import & Export")

# Sidebar - connection
st.sidebar.header("🔐 Odoo Connection")
url = st.sidebar.text_input("URL", placeholder="https://odoo.server.com")
db = st.sidebar.text_input("Database")
user = st.sidebar.text_input("Username")
password = st.sidebar.text_input("Password", type="password")

# Authenticate and connect
conn = None
if url and db and user and password:
    try:
        conn = OdooConnection(url, db, user, password)
        conn.authenticate()
        st.sidebar.success("Connected successfully")
    except Exception as e:
        st.sidebar.error(f"Connection failed: {e}")

# Main menu
if conn:
    mode = st.radio("Choose Mode", ["Export", "Import"])

    if mode == "Export":
        st.header("📤 Export Data from Odoo")
        models = conn.get_model_list()
        selected_model = st.selectbox("Select Model", models)

        if selected_model:
            fields_dict = conn.get_fields(selected_model, attributes=["string"])
            field_options = [(f"{v['string']} ({k})", k) for k, v in fields_dict.items()]
            field_labels, field_names = zip(*field_options) if field_options else ([], [])

            selected_fields = st.multiselect("Select fields to export", options=field_names, format_func=lambda x: dict(field_options).get(x, x))

            if st.button("Export"):
                try:
                    df = export_model_data(conn, selected_model, selected_fields)
                    st.success("Export completed.")
            
                    # ✅ Crear buffer Excel
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine="openpyxl") as writer:
                        df.to_excel(writer, index=False)
                    output.seek(0)
            
                    st.download_button(
                        label="Download Excel",
                        data=output,
                        file_name=f"{selected_model}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.error(f"Error during export: {e}")

    elif mode == "Import":
        st.header("📥 Import Data to Odoo")
        models = conn.get_model_list()
        selected_model = st.selectbox("Select Model", models)
        uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])
        operation_mode = st.radio("Operation Mode", ["create", "update"])

        if uploaded_file and selected_model:
            try:
                df = pd.read_excel(uploaded_file)
                st.dataframe(df.head())

                all_fields = list(df.columns)
                selected_fields = st.multiselect("Select fields to import", all_fields, default=all_fields)
                search_field = None
                if operation_mode == "update":
                    search_field = st.selectbox("Field to match for updates", [""] + selected_fields)
                    if search_field == "":
                        st.warning("You must select a field for update mode.")

                if st.button("Import"):
                    import_records(df[selected_fields], conn, selected_model, selected_fields, mode=operation_mode, search_field=search_field)
                    st.success("Import completed.")

            except Exception as e:
                st.error(f"Error reading Excel file: {e}")
else:
    st.info("Please complete the connection details to proceed.")
