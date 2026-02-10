import streamlit as st
import pandas as pd
import altair as alt
from datetime import timedelta

# === 1. Inicialización de Estado (Memoria de la App) ===
if 'meal_limit_hours' not in st.session_state:
    st.session_state['meal_limit_hours'] = 5.0 # CA Law: Break required if > 5.0 hours

if 'min_break_minutes' not in st.session_state:
    st.session_state['min_break_minutes'] = 30 # CA Law: 30 minutes

# === Función Lógica Principal ===
def process_csv_toast(file, limit_hours, min_break_hours, progress_bar=None):
    df = pd.read_csv(file)
    
    # 1. Limpieza inicial
    df = df.dropna(subset=['Employee', 'Date'])
    
    # 2. Parsers de Fecha y Hora Inteligentes
    def parse_dt(date_str, time_str):
        try:
            return pd.to_datetime(f"{date_str} {time_str}", format="%b %d, %Y %I:%M %p")
        except:
            return pd.NaT

    # Helper para manejar turnos que cruzan medianoche (PM -> AM)
    def parse_time_conditional(date_dt, time_str, ref_dt):
        if pd.isna(ref_dt) or pd.isna(time_str):
            return pd.NaT
        try:
            # Asumimos misma fecha primero
            dt = pd.to_datetime(f"{date_dt.strftime('%b %d, %Y')} {time_str}", format="%b %d, %Y %I:%M %p")
            # Si la hora es anterior al inicio del turno (ej. Start 8PM, Break 2AM), sumamos un día
            if dt < ref_dt:
                dt += timedelta(days=1)
            return dt
        except:
            return pd.NaT

    # Crear columna datetime para el inicio
    df['DateTime_In'] = df.apply(lambda row: parse_dt(row['Date'], row['Time In']), axis=1)
    
    # Convertir métricas a numérico
    cols_to_numeric = ['Total Hours', 'Regular Hours', 'Estimated Overtime', 'Break Duration']
    for col in cols_to_numeric:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

    # 3. Agrupación por Empleado y Día (Manejo de Double Clock-outs)
    grouped = df.groupby(['Employee', 'Date'])
    violations = []

    total_groups = len(grouped)
    processed_count = 0

    for (emp, date_str), group in grouped:
        processed_count += 1
        if progress_bar and processed_count % 10 == 0:
            progress_bar.progress(processed_count / total_groups, text="Analizando turnos complejos...")

        # Métricas del Día Completo (Agregado)
        total_hours = group['Total Hours'].sum()
        reg_hours = group['Regular Hours'].sum()
        ot_hours = group['Estimated Overtime'].sum()
        
        # Determinar el verdadero inicio del turno
        valid_starts = group['DateTime_In'].dropna()
        if valid_starts.empty:
            continue
        shift_start = valid_starts.min()
        
        # Recolectar TODOS los descansos válidos del día
        valid_breaks = []
        for _, row in group.iterrows():
            if row['Break Duration'] >= min_break_hours: 
                b_start = parse_time_conditional(shift_start, row['Break Start'], shift_start)
                if pd.notna(b_start):
                    valid_breaks.append(b_start)
        
        valid_breaks.sort()
        
        # === REGLAS DE AUDITORÍA ===
        
        violation_type = None
        details = ""

        # Regla 1: Violación de 1er Descanso (> 5 horas)
        if total_hours > limit_hours:
            deadline_5th = shift_start + timedelta(hours=limit_hours)
            
            if not valid_breaks:
                violation_type = "Missed Meal Break"
                details = f"Turno de {total_hours:.2f}h sin descanso válido."
            else:
                first_break = valid_breaks[0]
                if first_break > deadline_5th:
                    violation_type = "Late Meal Break"
                    break_time_str = first_break.strftime('%I:%M %p')
                    limit_str = deadline_5th.strftime('%I:%M %p')
                    details = f"Descanso a las {break_time_str} (Límite: {limit_str})"

        if violation_type:
            violations.append({
                "Nombre": emp,
                "Date": date_str,
                "Regular Hours": round(reg_hours, 2),
                "Overtime Hours": round(ot_hours, 2),
                "Total Horas Día": round(total_hours, 2),
                "Violación": violation_type,
                "Detalles": details
            })
        
        # Regla 2: Violación de 2do Descanso (> 10 horas)
        if total_hours > 10.0:
            deadline_10th = shift_start + timedelta(hours=10)
            
            if len(valid_breaks) < 2:
                waiver_status = "(Waivable)" if total_hours <= 12.0 else "(NON-Waivable >12h)"
                violations.append({
                    "Nombre": emp,
                    "Date": date_str,
                    "Regular Hours": round(reg_hours, 2),
                    "Overtime Hours": round(ot_hours, 2),
                    "Total Horas Día": round(total_hours, 2),
                    "Violación": "Missing 2nd Meal",
                    "Detalles": f"Turno > 10h. Solo {len(valid_breaks)} descansos. {waiver_status}"
                })
            elif len(valid_breaks) >= 2:
                second_break = valid_breaks[1]
                if second_break > deadline_10th:
                    violations.append({
                        "Nombre": emp,
                        "Date": date_str,
                        "Regular Hours": round(reg_hours, 2),
                        "Overtime Hours": round(ot_hours, 2),
                        "Total Horas Día": round(total_hours, 2),
                        "Violación": "Late 2nd Meal",
                        "Detalles": f"2do descanso tarde: {second_break.strftime('%I:%M %p')}"
                    })

    return pd.DataFrame(violations)

# === Configuración Streamlit ===
st.set_page_config(page_title="Auditoría Toast", page_icon="🌮", layout="wide")

# Sidebar
st.sidebar.title("Menú Principal")
menu = st.sidebar.radio("Navegación", ("Dashboard", "Configuración"))

# === Estilos CSS ===
st.markdown("""
    <style>
    body { background-color: #f4f6f9; }
    .metric-card {
        background: white; padding: 20px; border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center;
    }
    .card-title { font-size: 16px; color: #6c757d; }
    .card-value { font-size: 28px; font-weight: bold; color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

# === VISTA DASHBOARD ===
if menu == "Dashboard":
    st.markdown(f"""
        <h2 style='text-align: center;'>🛡️ Auditoría de Tiempos Toast</h2>
        <div style='text-align: center; color: gray; font-size: 0.9em; margin-bottom: 20px;'>
            Reglas Activas: Límite <b>{st.session_state['meal_limit_hours']}h</b> | 
            Descanso Mínimo <b>{st.session_state['min_break_minutes']} min</b>
        </div>
    """, unsafe_allow_html=True)

    file = st.file_uploader("Arrastra tu archivo CSV de Toast aquí", type=["csv"])

    if file:
        progress_bar = st.progress(0, text="Leyendo archivo...")
        min_break_hours = st.session_state['min_break_minutes'] / 60.0
        
        violations_df = process_csv_toast(
            file, 
            limit_hours=st.session_state['meal_limit_hours'],
            min_break_hours=min_break_hours,
            progress_bar=progress_bar
        )
        progress_bar.empty()

        if not violations_df.empty:
            st.success(f'✅ Análisis completado. Se encontraron {len(violations_df)} posibles violaciones.')
            
            # --- SECCIÓN 1: Métricas Globales ---
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"""<div class="metric-card"><div class="card-title">Total Incidencias</div><div class="card-value">{len(violations_df)}</div></div>""", unsafe_allow_html=True)
            with col2:
                st.markdown(f"""<div class="metric-card"><div class="card-title">Empleados Afectados</div><div class="card-value">{violations_df['Nombre'].nunique()}</div></div>""", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""<div class="metric-card"><div class="card-title">Late Breaks</div><div class="card-value">{len(violations_df[violations_df['Violación'].str.contains('Late')])}</div></div>""", unsafe_allow_html=True)

            # --- SECCIÓN 2: Reporte Agrupado (LO NUEVO) ---
            st.markdown("---")
            st.markdown("### 📊 Resumen Ejecutivo por Empleado")
            
            # Crear tabla pivote: Filas=Empleados, Columnas=Tipo de Violación, Valores=Conteo
            summary_df = violations_df.groupby(['Nombre', 'Violación']).size().unstack(fill_value=0)
            summary_df['Total Violaciones'] = summary_df.sum(axis=1) # Suma total por fila
            summary_df = summary_df.sort_values('Total Violaciones', ascending=False).reset_index()
            
            col_summary_table, col_summary_chart = st.columns([1.5, 1])
            
            with col_summary_table:
                st.dataframe(summary_df, use_container_width=True)
                
                # Botón de descarga para el resumen agrupado
                csv_summary = summary_df.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇️ Descargar Resumen Agrupado (CSV)", 
                    data=csv_summary, 
                    file_name="resumen_violaciones_por_empleado.csv", 
                    mime="text/csv",
                    help="Descarga una tabla con el total de violaciones por cada empleado."
                )

            with col_summary_chart:
                 chart = alt.Chart(summary_df).mark_bar(color="#ff6b6b").encode(
                    x=alt.X('Total Violaciones', title='Cantidad'),
                    y=alt.Y('Nombre', sort='-x', title=''),
                    tooltip=['Nombre', 'Total Violaciones']
                ).properties(height=350)
                 st.altair_chart(chart, use_container_width=True)


            # --- SECCIÓN 3: Detalle Completo ---
            st.markdown("---")
            st.markdown("### 📋 Detalle de Incidencias (Fila por Fila)")
            
            st.dataframe(
                violations_df.style.applymap(
                    lambda x: 'color: red; font-weight: bold' if 'Missing' in str(x) else ('color: orange' if 'Late' in str(x) else ''), 
                    subset=['Violación']
                ), 
                use_container_width=True
            )

            csv_full = violations_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Descargar Detalle Completo (CSV)", data=csv_full, file_name="detalle_meal_break.csv", mime="text/csv")
        
        else:
            st.balloons()
            st.success("🎉 ¡Excelente! No se encontraron violaciones bajo las reglas actuales.")

# === VISTA CONFIGURACIÓN ===
elif menu == "Configuración":
    st.header("⚙️ Configuración de Reglas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Parámetros de Meal Penalty")
        new_limit = st.number_input(
            "Hora límite para iniciar descanso (California = 5.0)",
            min_value=4.0, max_value=8.0, 
            value=st.session_state['meal_limit_hours'], step=0.5
        )
        
        new_break_min = st.number_input(
            "Duración mínima válida del descanso (Minutos)",
            min_value=10, max_value=60, 
            value=int(st.session_state['min_break_minutes']), step=5
        )
        
        if st.button("💾 Guardar Cambios"):
            st.session_state['meal_limit_hours'] = new_limit
            st.session_state['min_break_minutes'] = new_break_min
            st.success("Reglas actualizadas. Vuelve al Dashboard para re-analizar.")

    with col2:
        st.info("""
        **Guía Rápida:**
        * **5.0 Horas:** En CA, el descanso debe comenzar *antes* de terminar la 5ta hora de trabajo.
        * **Double Clock-outs:** El sistema ahora agrupa automáticamente turnos partidos en el mismo día.
        * **Resumen Agrupado:** Ahora puedes descargar una tabla de totales por empleado en la sección principal.
        """)
