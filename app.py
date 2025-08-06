import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time

# === Función para procesar CSV de Toast ===
def process_csv_toast(file, progress_bar=None):
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

    df = df[df['Employee'].notna() & df['Date'].notna()]  # Filtrar registros nulos en 'Employee' y 'Date'

    # Convertir las columnas de fecha y hora
    def parse_datetime(row, date_col, time_col):
        try:
            return pd.to_datetime(f"{row[date_col]} {row[time_col]}", format="%b %d, %Y %I:%M %p")
        except:
            return pd.NaT

    df["Clock In"] = df.apply(lambda row: parse_datetime(row, "Date", "Time In"), axis=1)
    df["Clock Out"] = df.apply(lambda row: parse_datetime(row, "Date", "Time Out"), axis=1)

    # Convertir 'Regular Hours' y 'Estimated Overtime' a números
    df["Regular Hours"] = pd.to_numeric(df["Regular Hours"], errors='coerce')
    df["Estimated Overtime"] = pd.to_numeric(df.get("Estimated Overtime", 0), errors='coerce').fillna(0)

    # Calcular 'Total Hours' sumando las horas regulares y las horas extras
    df["Total Hours"] = df["Regular Hours"] + df["Estimated Overtime"]
    df["Date"] = df["Clock In"].dt.date

    grouped = df.groupby(["Employee", "Date"])  # Agrupar por empleado y fecha
    violations = []

    for (name, date), group in grouped:
        total_hours = group["Total Hours"].sum()

        # Criterio 1: Si trabajó más de 6 horas y no tomó descanso
        if total_hours > 6:
            on_breaks = group.query('`Clock Out Status` == "On break"')
            if on_breaks.empty:
                violations.append({
                    "Nombre": name,
                    "Date": date,
                    "Regular Hours": "No Break Taken",
                    "Overtime Hours": round(group["Estimated Overtime"].sum(), 2),
                    "Total Horas Día": round(total_hours, 2),
                    "Violación": "No Break Taken"
                })
        
        # Criterio 2: Si trabajó más de 5 horas y el descanso fue después de ese tiempo
        elif total_hours > 5:
            on_breaks = group.query('`Clock Out Status` == "On break"')
            if not on_breaks.empty:
                first_break = on_breaks.iloc[0]
                if first_break["Regular Hours"] > 5:  # Si el primer descanso es después de 5 horas
                    violations.append({
                        "Nombre": name,
                        "Date": date,
                        "Regular Hours": round(first_break["Regular Hours"], 2),
                        "Overtime Hours": round(group["Estimated Overtime"].sum(), 2),
                        "Total Horas Día": round(total_hours, 2),
                        "Violación": "Break After 5 Hours"
                    })

    return pd.DataFrame(violations)

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

# === Encabezado personalizado ===
if menu == "Dashboard":
    st.markdown("""
        <h1 style='text-align: center; color: #343a40;'>🍳 Meal Violations Dashboard</h1>
        <p style='text-align: center; color: #6c757d;'>Based on Toast Time Entries CSV – By Jordan Memije</p>
        <hr style='margin-top: 0px;'>
    """, unsafe_allow_html=True)

    file = st.file_uploader("📤 Sube tu archivo CSV de Time Entries exportado desde Toast", type=["csv"])

    if file:
        progress_bar = st.progress(0, text="Iniciando análisis...")
        violations_df = process_csv_toast(file, progress_bar)
        progress_bar.empty()

        st.balloons()
        st.success('✅ Análisis completado.')

        total_violations = len(violations_df)
        unique_employees = violations_df['Nombre'].nunique()
        dates_analyzed = violations_df['Date'].nunique()

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

        violation_counts = violations_df["Nombre"].value_counts().reset_index()
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

elif menu == "Configuración":
    st.markdown("# ⚙️ Configuración")
    st.info("Opciones de configuración próximamente disponibles.")
