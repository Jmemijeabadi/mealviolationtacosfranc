import streamlit as st
import requests
import pandas as pd

# ⛓️ Autenticación con Toast OAuth2 (Client Credentials Flow)
def get_access_token(client_id, client_secret):
    token_url = "https://ws-api.toasttab.com/oauth/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "client_credentials",
        "scope": "toast.all.apis"  # o los scopes habilitados
    }

    try:
        response = requests.post(token_url, json=payload)
        response.raise_for_status()
        token = response.json()["access_token"]
        return token
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error obteniendo token de acceso: {e}")
        return None

# 🔍 Consulta a API de Toast (ejemplo: obtener empleados)
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
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Error consultando empleados: {e}")
        return []

# 🖥️ UI Streamlit
st.set_page_config(page_title="Toast API – Meal Violations", layout="centered")
st.title("🍔 Meal Break Violations – API Toast")
st.markdown("Autenticación y prueba de conexión a Toast API usando OAuth2.")

# 🔐 Leer credenciales desde secrets
client_id = st.secrets.get("TOAST_CLIENT_ID", "")
client_secret = st.secrets.get("TOAST_CLIENT_SECRET", "")

if not client_id or not client_secret:
    st.error("⚠️ Falta el client_id o client_secret en secrets.")
    st.stop()

# 🪪 Obtener token y llamar a API
token = get_access_token(client_id, client_secret)

if token:
    st.success("✅ Token obtenido correctamente.")

    with st.spinner("Consultando empleados..."):
        employees = get_employees(token)
        if employees:
            df = pd.DataFrame(employees)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("No se encontraron empleados.")
