import streamlit as st
import requests
import pandas as pd

# — Streamlit config
st.set_page_config(page_title="Toast API – Meal Violations", layout="wide")
st.title("🍔 Meal Violations – Toast API")
st.markdown("Autenticación con TOAST_MACHINE_CLIENT vía token + consulta de empleados.")

# 🔐 Secrets
client_id = st.secrets.get("TOAST_CLIENT_ID", "")
client_secret = st.secrets.get("TOAST_CLIENT_SECRET", "")

if not client_id or not client_secret:
    st.error("Faltan TOAST_CLIENT_ID o TOAST_CLIENT_SECRET en tus secrets.")
    st.stop()

# ✅ Obtener token
def get_access_token(client_id, client_secret):
    url = "https://ws-api.toasttab.com/usermgmt/v1/oauth/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "user_access_type": "TOAST_MACHINE_CLIENT"
    }
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        return res.json()["token"]["accessToken"]
    except Exception as e:
        st.error(f"❌ Error al obtener token: {e}")
        return None

# 📡 Consultar empleados
def get_employees(token):
    url = "https://ws-api.toasttab.com/labor/v1/employees"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.get(url, headers=headers)
        res.raise_for_status()
        return res.json().get("employees", [])
    except Exception as e:
        st.error(f"❌ Error al consultar empleados: {e}")
        return []

# 🚀 Flujo principal
token = get_access_token(client_id, client_secret)
if token:
    st.success("✅ Token de acceso obtenido correctamente.")

    if st.button("🔍 Consultar empleados"):
        with st.spinner("Cargando desde Toast..."):
            employees = get_employees(token)
            if employees:
                df = pd.DataFrame(employees)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("No se encontraron empleados.")
