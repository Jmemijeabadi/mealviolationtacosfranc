import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import time
import altair as alt # Recomendado para gráficos mejores

# === 1. Inicialización de Estado (Memoria de la App) ===
if 'meal_limit_hours' not in st.session_state:
    st.session_state['meal_limit_hours'] = 6.0 # Default: 6 horas

if 'min_break_minutes' not in st.session_state:
    st.session_state['min_break_minutes'] = 30 # Default: 30 minutos

# === Función para procesar CSV de Toast (Actualizada) ===
# Ahora recibe limit_hours y min_break_hours como argumentos
def process_csv_toast(file, limit_hours, min_break_hours, progress_bar=None):
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
            # time.sleep(0.4) # Comentado para hacerlo más rápido, descomenta si prefieres el efecto

    df = df[df['Employee'].notna() & df['Date'].notna()]

    def parse_datetime(row, date_col, time_col):
        try:
            return pd.to_datetime(f"{row[date_col]} {row[time_col]}", format="%b %d, %Y %I:%M %p")
        except:
            return pd.NaT

    df["Clock In"] = df.apply(lambda row: parse_datetime(row, "Date", "Time In"), axis=1)
    df["Clock Out"] = df.apply(lambda row: parse_datetime(row, "Date", "Time Out"), axis=1)

    df["Regular Hours"] = pd.to_numeric(df["Regular Hours"], errors='coerce')
    df["Estimated Overtime"] = pd.to_numeric(df.get("Estimated Overtime", 0), errors='coerce').fillna(0)
    
    df["Total Hours"] = df["Regular Hours"] + df["Estimated Overtime"]
    df["Date"] = df["Clock In"].dt.date

    df["Break Duration"] = pd.to_numeric(df["Break Duration"], errors='coerce') 

    grouped = df.groupby(["Employee", "Date"]) 
    violations = []

    for (name, date), group in grouped:
        total_hours = group["Total Hours"].sum()

        # === Lógica Dinámica ===
        # Usamos la variable min_break_hours pasada como argumento
        missed_break = group[(group["Break Duration"].isna()) | 
                             (group["Break Duration"] < min_break_hours) | # <--- DYNAMIC
                             (group["Break Duration"] == "MISSED")]

        # Usamos la variable limit_hours pasada como argumento
        if not missed_break.empty and total_hours > limit_hours: # <--- DYNAMIC
            violations.append({
                "Nombre": name,
                "Date": date,
                "Regular Hours": round(group["Regular Hours"].sum(), 2),
                "Overtime Hours": round(group["Estimated Overtime"].sum(), 2),
                "Total Horas Día": round(total_hours, 2),
                "Violación": "Meal Violation"
            })

    return pd.DataFrame(violations)

# === Configuración Streamlit ===
st.set_page_config(page_title="Meal Violations Toast", page_icon="🌮", layout="wide")

# Sidebar
st.sidebar.title("Menú Principal")
menu = st.sidebar.radio("Navegación", ("Dashboard", "Configuración"))

# === Estilos Freedash ===
st.markdown("""
    <style>
    body { background-color: #f4f6f9; }
    header, footer {visibility: hidden;}
    .block-container { padding-top: 2rem; }
    .metric-card {
        background: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center;
    }
    .card-title { font-size: 18px; color: #6c757d; margin-bottom: 0.5rem; }
    .card-value { font-size: 30px; font-weight: bold; color: #343a40; }
    .stButton > button {
        background-color: #009efb; color: white; padding: 0.75rem 1.5rem;
        border: none; border-radius: 8px; font-weight: bold; width: 100%;
    }
    .stButton > button:hover { background-color: #007acc; color: white; }
    </style>
""", unsafe_allow_html=True)

# === Dashboard principal ===
if menu == "Dashboard":
    st.markdown("""
        <h1 style='text-align: center; color: #343a40;'>Meal Violations Detector</h1>
        <p style='text-align: center; color: #6c757d;'>
            Reglas actuales: Turnos > <b>{}h</b> | Descanso mín: <b>{} min</b>
        </p>
        <hr style='margin-top: 0px;'>
    """.format(st.session_state['meal_limit_hours'], st.session_state['min_break_minutes']), unsafe_allow_html=True)

    file = st.file_uploader("📤 Sube tu archivo CSV de Toast", type=["csv"])

    if file:
        progress_bar = st.progress(0, text="Iniciando análisis...")
        
        # Convertimos minutos a horas para la lógica (ej. 30 min / 60 = 0.5h)
        min_break_hours = st.session_state['min_break_minutes'] / 60.0
        
        # Pasamos las variables de session_state a la función
        violations_df = process_csv_toast(
            file, 
            limit_hours=st.session_state['meal_limit_hours'],
            min_break_hours=min_break_hours,
            progress_bar=progress_bar
        )
        progress_bar.empty()

        if not violations_df.empty:
            st.success('✅ Análisis completado.')
            
            total_violations = len(violations_df)
            unique_employees = violations_df['Nombre'].nunique()
            dates_analyzed = violations_df['Date'].nunique()

            st.markdown("## 📈 Resumen General")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown(f"""<div class="metric-card"><div class="card-title">Violaciones Detectadas</div><div class="card-value">{total_violations}</div></div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""<div class="metric-card"><div class="card-title">Empleados Afectados</div><div class="card-value">{unique_employees}</div></div>""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""<div class="metric-card"><div class="card-title">Días Analizados</div><div class="card-value">{dates_analyzed}</div></div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("## 📋 Detalle de Violaciones")
            st.dataframe(violations_df, use_container_width=True)

            violation_counts = violations_df["Nombre"].value_counts().reset_index()
            violation_counts.columns = ["Empleado", "Número de Violaciones"]

            st.markdown("## 📊 Violaciones por Empleado")
            col_graph, col_table = st.columns([2, 1])

            with col_graph:
                # Versión interactiva (más moderna)
                chart = alt.Chart(violation_counts).mark_bar(color="#009efb", cornerRadiusEnd=5).encode(
                    x=alt.X('Número de Violaciones', title='Total Violaciones'),
                    y=alt.Y('Empleado', sort='-x', title=''),
                    tooltip=['Empleado', 'Número de Violaciones']
                ).properties(height=400)
                st.altair_chart(chart, use_container_width=True)

            with col_table:
                st.dataframe(violation_counts, use_container_width=True)

            csv = violations_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Descargar CSV", data=csv, file_name="meal_violations.csv", mime="text/csv")
        else:
            st.balloons()
            st.success("¡Felicidades! No se encontraron violaciones con los parámetros actuales.")

# === Pestaña de Configuración ===
elif menu == "Configuración":
    st.markdown("# ⚙️ Configuración de Auditoría")
    st.markdown("Ajusta las reglas para la detección de violaciones.")
    
    st.markdown("---")
    
    col_config1, col_config2 = st.columns(2)
    
    with col_config1:
        st.markdown("### 🕒 Reglas de Turno")
        
        # Input para Horas Totales
        new_limit = st.number_input(
            "Límite de horas para exigir Meal Break (Horas)",
            min_value=4.0, 
            max_value=12.0, 
            value=st.session_state['meal_limit_hours'],
            step=0.5,
            help="Si un empleado trabaja más de estas horas, debe tener un descanso registrado."
        )
        
        # Input para Duración del Descanso
        new_break_min = st.number_input(
            "Duración mínima aceptable del descanso (Minutos)", 
            min_value=10, 
            max_value=60, 
            value=int(st.session_state['min_break_minutes']),
            step=5,
            help="Cualquier descanso menor a esto se considerará una violación."
        )

        # Botón para guardar
        if st.button("💾 Guardar Configuración"):
            st.session_state['meal_limit_hours'] = new_limit
            st.session_state['min_break_minutes'] = new_break_min
            st.success("Configuración actualizada. Vuelve al Dashboard para analizar con las nuevas reglas.")

    with col_config2:
        st.info(f"""
        **Configuración Actual:**
        
        * **Límite de turno:** > {st.session_state['meal_limit_hours']} horas
        * **Descanso mínimo:** {st.session_state['min_break_minutes']} minutos
        
        Si cambias estos valores, asegúrate de presionar "Guardar" y volver a cargar tu archivo en el Dashboard.
        """)
        
        # Botón de Reset
        if st.button("🔄 Restaurar valores por defecto"):
            st.session_state['meal_limit_hours'] = 6.0
            st.session_state['min_break_minutes'] = 30
            st.rerun()
