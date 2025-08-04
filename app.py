import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# ✅ Leer API Key desde Streamlit Secrets (agrega esto en tu Panel de Streamlit Cloud)
TOAST_API_KEY = st.secrets["TOAST_API_KEY"]

# 📡 Configuración base
BASE_URL = "https://api.toasttab.com/labor/v1"
HEADERS = {
    "Authorization": f"Bearer {TOAST_API_KEY}",
    "Content-Type": "application/json"
}

# 🔄 Obtener turnos desde la API de Toast
def get_shifts(start_date, end_date):
    url = f"{BASE_URL}/shifts?startDate={start_date}&endDate={end_date}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("shifts", [])

# ⚠️ Validar violaciones según ley laboral de California
def detect_meal_violations(shifts):
    results = []
    for shift in shifts:
        try:
            start = datetime.fromisoformat(shift["startDateTime"])
            end = datetime.fromisoformat(shift["endDateTime"])
            worked_hours = (end - start).total_seconds() / 3600
            breaks = shift.get("breaks", [])
            long_breaks = [b for b in breaks if b["durationMinutes"] >= 30]

            violation = False
            reason = "—"
            if worked_hours > 5 and len(long_breaks) < 1:
                violation = True
                reason = "No meal break after 5 hours"
            if worked_hours > 10 and len(long_breaks) < 2:
                violation = True
                reason = "Only one meal break after 10 hours"

            results.append({
                "Employee ID": shift["employeeId"],
                "Start": start,
                "End": end,
                "Hours Worked": round(worked_hours, 2),
                "Breaks (30+ min)": len(long_breaks),
                "Violation": violation,
                "Reason": reason
            })
        except Exception as e:
            results.append({
                "Employee ID": shift.get("employeeId", "Unknown"),
                "Start": "Error",
                "End": "Error",
                "Hours Worked": 0,
                "Breaks (30+ min)": 0,
                "Violation": True,
                "Reason": f"Error parsing shift: {e}"
            })
    return pd.DataFrame(results)

# 🖥️ Interfaz Streamlit
st.set_page_config(page_title="Meal Violations", layout="wide")
st.title("🍔 Meal Break Violations – Ley de California")
st.markdown("Esta herramienta identifica violaciones de pausas para comer basadas en las leyes laborales de California.")

# 🗓️ Selección de fechas
col1, col2 = st.columns(2)
start_date = col1.date_input("📅 Fecha de inicio", datetime.now() - timedelta(days=7))
end_date = col2.date_input("📅 Fecha de fin", datetime.now())

# Validación de rango de fechas
if start_date > end_date:
    st.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
    st.stop()

# 🔘 Botón de análisis
if st.button("📊 Analizar turnos"):
    with st.spinner("Conectando a Toast y analizando datos..."):
        try:
            shifts = get_shifts(start_date.isoformat(), end_date.isoformat())
            df = detect_meal_violations(shifts)

            st.success(f"{len(df)} turnos analizados.")
            st.dataframe(df, use_container_width=True)

            # 📥 Exportar como CSV
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Descargar CSV", csv, "meal_violations.csv", "text/csv")
        except Exception as e:
            st.error(f"❌ Error al obtener los turnos: {e}")
