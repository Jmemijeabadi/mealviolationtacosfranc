import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time

# === Función para procesar CSV de Toast ===
def process_csv_toast(file, start_date, end_date, progress_bar=None):
    df = pd.read_csv(file)

    steps = [
        ("📂 Cargando archivo...", 0.2),
        ("⏱️ Convirtiendo horarios...", 0.4),
        ("🧮 Calculando horas totales...", 0.6),
        ("🔍 Buscando violaciones...", 0.8),
        ("✅ Finalizando...", 1.0)
    ]

    if progress_bar:
        for msg, pct in steps:
            progress_bar.progress(pct, text=msg)
            time.sleep(0.4)

    # Limpiar cualquier espacio en blanco en los nombres de las columnas
    df.columns = df.columns.str.strip()

    # Filtrar solo las filas que contienen valores en 'Employee' y 'Date'
    df = df[df['Employee'].notna() & df['Date'].notna()]

    # Convertir la columna 'Date' en formato datetime
    df['Date'] = pd.to_datetime(df['Date'], format="%b %d, %Y")

    # Convertir las fechas de inicio y fin a datetime64 (asegúrate que están en formato pandas datetime)
    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    # Filtrar por el rango de fechas seleccionado
    df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]

    # Convertir las columnas 'Clock In' y 'Clock Out' en datetime
    def parse_datetime(row, date_col, time_col):
        try:
            return pd.to_datetime(f"{row[date_col]} {row[time_col]}", format="%b %d, %Y %I:%M %p")
        except:
            return pd.NaT

    df["Clock In"] = df.apply(lambda row: parse_datetime(row, "Date", "Time In"), axis=1)
    df["Clock Out"] = df.apply(lambda row: parse_datetime(row, "Date", "Time Out"), axis=1)

    # Asegurar que las horas sean números válidos
    df["Regular Hours"] = pd.to_numeric(df["Regular Hours"], errors='coerce')
    df["Estimated Overtime"] = pd.to_numeric(df.get("Estimated Overtime", 0), errors='coerce').fillna(0)

    # Calcular las horas totales
    df["Total Hours"] = df["Regular Hours"] + df["Estimated Overtime"]
    df["Date"] = df["Clock In"].dt.date

    # Normalizar nombres de columnas (quitar espacios y convertir a minúsculas)
    df.columns = df.columns.str.strip().str.lower()

    # Verificar que 'employee' esté presente
    if 'employee' in df.columns:
        # Agrupar los datos por empleado y fecha
        grouped = df.groupby(["employee", "date"])
        violations = []

        # Buscar violaciones
        for (name, date), group in grouped:
            total_hours = group["total hours"].sum()
            if total_hours <= 6:
                continue  # Si las horas son menores o iguales a 6, no se consideran violaciones

            # Buscar si hay un 'MISSED BREAK' en las anomalías
            anomaly = group["anomalies"].astype(str).str.contains("MISSED BREAK").any()
            if anomaly:
                violations.append({
                    "Empleado": name,
                    "Fecha": date,
                    "Horas Regulares": round(group["regular hours"].sum(), 2),
                    "Horas Overtime": round(group["estimated overtime"].sum(), 2),
                    "Total Horas Día": round(total_hours, 2),
                    "Violación": "MISSED BREAK"
                })

        return pd.DataFrame(violations)
    else:
        st.error("No se encontró la columna 'Employee'. Revisa los datos.")
        st.stop()

# === Configuración Streamlit ===
st.set_page_config(page_title="Meal Violations Toast", page_icon="🍳", layout="wide")

# Sidebar
st.sidebar.title("Menú Principal")
menu = st.sidebar.radio("Navegación", ("Dashboard", "Configuración"))

# === Estilos Freedash ===
st.markdown("""
    <style>
    body {
        background-color: #f4f6f9;
    }
    header, footer {visibility: hidden;}
    .block-container {
        padding-top: 2rem;
    }
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
    }
    .card-title {
        font-size: 18px;
        color: #6c757d;
        margin-bottom: 0.5rem;
    }
    .card-value {
        font-size: 30px;
        font-weight: bold;
        color: #343a40;
    }
    .stButton > button {
        background-color: #009efb;
        color: white;
        padding: 0.75rem 1.5rem;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #007acc;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# === Dashboard principal ===
if menu == "Dashboard":
    st.markdown("""
        <h1 style='text-align: center; color: #343a40;'>🍳 Meal Violations Dashboard</h1>
        <p style='text-align: center; color: #6c757d;'>Based on Toast Time Entries CSV – By Jordan Memije</p>
        <hr style='margin-top: 0px;'>
    """, unsafe_allow_html=True)

    # Subir archivo
    file = st.file_uploader("📤 Sube tu archivo CSV de Time Entries exportado desde Toast", type=["csv"])

    # Selección de fechas
    st.markdown("### 🔥 Filtrar por rango de fechas")
    start_date = st.date_input("Fecha de inicio", pd.to_datetime("2025-07-01"))
    end_date = st.date_input("Fecha de fin", pd.to_datetime("2025-07-31"))

    if file:
        progress_bar = st.progress(0, text="Iniciando análisis...")
        violations_df = process_csv_toast(file, start_date, end_date, progress_bar)
        progress_bar.empty()

        st.balloons()
        st.success('✅ Análisis completado.')

        total_violations = len(violations_df)
        unique_employees = violations_df['Empleado'].nunique()  # Usando "Empleado"
        dates_analyzed = violations_df['Fecha'].nunique()

        st.markdown("## 📈 Resumen General")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="card-title">Violaciones Detectadas</div>
                    <div class="card-value">{total_violations}</div>
                </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="card-title">Empleados Afectados</div>
                    <div class="card-value">{unique_employees}</div>
                </div>
            """, unsafe_allow_html=True)

        with col3:
            st.markdown(f"""
                <div class="metric-card">
                    <div class="card-title">Días Analizados</div>
                    <div class="card-value">{dates_analyzed}</div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## 📋 Detalle de Violaciones")
        st.dataframe(violations_df, use_container_width=True)

        violation_counts = violations_df["Empleado"].value_counts().reset_index()  # Usando "Empleado"
        violation_counts.columns = ["Empleado", "Número de Violaciones"]

        st.markdown("## 📊 Violaciones por Empleado")
        col_graph, col_table = st.columns([2, 1])

        with col_graph:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.barh(violation_counts["Empleado"], violation_counts["Número de Violaciones"], color="#009efb")
            ax.set_xlabel("Número de Violaciones")
            ax.set_ylabel("Empleado")
            ax.set_title("Violaciones por Empleado", fontsize=14)
            st.pyplot(fig)

        with col_table:
            st.dataframe(violation_counts, use_container_width=True)

        st.markdown("---")

        high_violators = violation_counts[violation_counts["Número de Violaciones"] > 10]
        if not high_violators.empty:
            st.error("🚨 Atención: Hay empleados con más de 10 violaciones detectadas!")
            st.dataframe(high_violators, use_container_width=True)

        csv = violations_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Descargar resultados en CSV",
            data=csv,
            file_name="meal_violations.csv",
            mime="text/csv"
        )

    else:
        st.info("📤 Por favor sube un archivo CSV exportado desde Toast para comenzar.")
