import streamlit as st
import requests
import pandas as pd

# 📌 Endpoint de autenticación Toast
TOKEN_URL = "https://ws-api.toasttab.com/usermgmt/v1/oauth/token"
API_BASE = "https://ws-api.toasttab.com/labor/v1"

def get_access_token(client_id, client_secret):
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "user_access_type": "TOAST_MACHINE_CLIENT"
    }
    try:
        res = requests.post(TOKEN_URL, json=payload)
        res.raise_for_status()
        return res.json()["token"]["accessToken"]
    except Exception as e:
        st.error(f"❌ Error al obtener token: {e}")
        return None

def get_employees(token, location_guid=None):
    url = API_BASE + "/employees"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    params = {"locationGuid": location_guid} if location_guid else {}
    try:
        r = requests.get(url, headers=headers, params=params)
        r.raise_for_status()
        return r.json().get("employees", [])
    except Exception as e:
        st.error(f"❌ Error consultando empleados: {e}")
        return []

# ——— Streamlit UI ———
st.set_page_config(page_title="Toast Meal Violations", layout="wide")
st.title("🍔 Meal Violations – Toast API (Machine Client)")
st.markdown("Usa client credentials para obtener token y conectar con Toast.")

client_id = st.secrets.get("TOAST_CLIENT_ID", "")
client_secret = st.secrets.get("TOAST_CLIENT_SECRET", "")
location_guid = st.text_input("GUID de la ubicación (opcional)", "")

if not client_id or not client_secret:
    st.error("Por favor configura TOAST_CLIENT_ID y TOAST_CLIENT_SECRET en secrets.toml o panel de Streamlit.")
    st.stop()

token = get_access_token(client_id, client_secret)
if not token:
    st.stop()
st.success("✅ Token obtenido")

if st.button("Cargar empleados"):
    with st.spinner("Consultando empleados..."):
        employees = get_employees(token, location_guid or None)
        if employees:
            df = pd.DataFrame(employees)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No se encontraron empleados o no tienes acceso a esa ubicación.")
