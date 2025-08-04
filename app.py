import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timedelta

# Configuración
TOAST_API_KEY = st.secrets["pq-SvCvMGg7SJnWLzy81ZIxH7b1TzqDs19sltq6Ltw2CZ9-gm6zx-q1lUcY0gSYF"]
BASE_URL = "https://api.toasttab.com/labor/v1"
HEADERS = {
    "Authorization": f"Bearer {TOAST_API_KEY}",
    "Content-Type": "application/json"
}

def get_shifts(start_date, end_date):
    url = f"{BASE_URL}/shifts?startDate={start_date}&endDate={end_date}"
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()
    return response.json().get("shifts", [])

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
                "Employee ID": shift.get("employeeId", "unknown"),
                "Start": "ERROR",
                "End": "ERROR",
                "Hours Worked": 0,
                "Breaks (30+ min)": 0,
                "Violation": True,
                "Reason": f"Error parsing shift: {e}"
            })
    return pd.DataFrame(results)

# UI
st.title("🍔 Meal Break Violations – California Labor Law")
st.markdown("Detecta violaciones de pausas para comer según las leyes de California.")

col1, col2 = st.columns(2)
start_date = col1.date_input("Start Date", datetime.now() - timedelta(days=7))
end_date = col2.date_input("End Date", datetime.now())

if start_date > end_date:
    st.error("Start date must be before end date.")
else:
    if st.button("📊 Analizar turnos"):
        with st.spinner("Conectando a Toast API y analizando..."):
            try:
                shifts = get_shifts(start_date.isoformat(), end_date.isoformat())
                df = detect_meal_violations(shifts)
                st.success(f"{len(df)} turnos analizados.")
                st.dataframe(df, use_container_width=True)

                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Descargar CSV", csv, "meal_violations.csv", "text/csv")
            except Exception as e:
                st.error(f"Error al procesar: {e}")

