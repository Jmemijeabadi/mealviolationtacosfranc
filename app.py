import streamlit as st
import requests
import pandas as pd

st.set_page_config(page_title="Toast API – Meal Violations", layout="wide")
st.title("🍔 Meal Violations – Conexión directa a Toast API")
st.markdown("Esta app conecta directamente a Toast usando `clientId`, `clientSecret` y `userAccessType` como headers.")

# 🔐 Leer credenciales desde secrets
client_id = st.secrets.get("TOAST_CLIENT_ID", "")
client_secret = st.secrets.get("TOAST_CLIENT_SECRET", "")

if not client_id or not client_secret:
    st.error("Faltan TOAST_CLIENT_ID o TOAST_CLIENT_SECRET en tus secrets.")
    st.stop()

# ✅ Función para llamar directo a Toast API
def get_employees_direct(client_id, client_secret):
    url = "https://ws-api.toasttab.com/labor/v1/employees"
    headers = {
        "Content-Type": "application/json",
        "userAccessType": "TOAST_MACHINE_CLIENT",
        "clientId": client_id,
        "clientSecret": client_secret
    }

    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json().get("employees", [])

if st.button("📋 Consultar empleados"):
    with st.spinner("Conectando a Toast..."):
        try:
            employees = get_employees_direct(client_id, client_secret)
            if employees:
                df = pd.DataFrame(employees)
                st.success(f"{len(df)} empleados encontrados.")
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No se encontraron empleados.")
        except Exception as e:
            st.error(f"❌ Error al consultar: {e}")
