import streamlit as st
import pandas as pd

st.set_page_config(page_title="Meal Violations – Toast", layout="wide")
st.title("🍔 Meal Violations – Ley de California (Archivo Time Entries)")
st.markdown("Sube un archivo CSV exportado desde Toast con datos de Time Entries para analizar violaciones de descanso para comer.")

uploaded_file = st.file_uploader("📂 Sube archivo CSV", type=["csv"])

if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file)

        # Limpiar filas vacías
        df = df[df['Employee'].notna() & df['Date'].notna()]

        # Convertir a datetime
        def parse_datetime(row, date_col, time_col):
            try:
                return pd.to_datetime(f"{row[date_col]} {row[time_col]}", format="%b %d, %Y %I:%M %p")
            except:
                return pd.NaT

        df["Shift Start"] = df.apply(lambda row: parse_datetime(row, "Date", "Time In"), axis=1)
        df["Shift End"] = df.apply(lambda row: parse_datetime(row, "Date", "Time Out"), axis=1)
        df["Hours Worked"] = (df["Shift End"] - df["Shift Start"]).dt.total_seconds() / 3600

        def parse_break_duration(val):
            try:
                return float(val) * 60
            except:
                return 0.0

        df["Break Minutes"] = df["Break Duration"].apply(parse_break_duration)

        def detect_violation(hours, break_minutes):
            if pd.isna(hours):
                return "Invalid"
            if hours > 10 and break_minutes < 60:
                return "❌ 2 required breaks (>10h)"
            elif hours > 5 and break_minutes < 30:
                return "❌ 1 required break (>5h)"
            else:
                return "✅ OK"

        df["Meal Violation"] = df.apply(lambda row: detect_violation(row["Hours Worked"], row["Break Minutes"]), axis=1)

        # Columnas finales
        result_df = df[[
            "Employee", "Date", "Shift Start", "Shift End", "Hours Worked",
            "Break Start", "Break End", "Break Duration", "Anomalies", "Meal Violation"
        ]].copy()

        st.success(f"{len(result_df)} turnos analizados.")
        st.dataframe(result_df, use_container_width=True)

        # Descargar CSV
        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Descargar CSV con Violaciones", csv, "meal_violations.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ Error al procesar el archivo: {e}")
