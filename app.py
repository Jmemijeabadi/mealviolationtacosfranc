import streamlit as st
import pandas as pd
import altair as alt
from datetime import timedelta

# === 1. Inicialización de Estado ===
if 'meal_deadline_hours' not in st.session_state:
    st.session_state['meal_deadline_hours'] = 5.0 # La ley exige descanso antes de la 5ta hora

if 'waiver_limit_hours' not in st.session_state:
    st.session_state['waiver_limit_hours'] = 6.0 # Se puede renunciar al descanso si el turno es <= 6h

if 'min_break_minutes' not in st.session_state:
    st.session_state['min_break_minutes'] = 30 

# === Función Lógica Principal ===
def process_csv_toast(file, deadline_hours, waiver_limit, min_break_hours, progress_bar=None):
    df = pd.read_csv(file)
    df = df.dropna(subset=['Employee', 'Date'])
    
    # --- Parsers ---
    def parse_dt(date_str, time_str):
        try:
            return pd.to_datetime(f"{date_str} {time_str}", format="%b %d, %Y %I:%M %p")
        except:
            return pd.NaT

    def parse_time_conditional(date_dt, time_str, ref_dt):
        if pd.isna(ref_dt) or pd.isna(time_str):
            return pd.NaT
        try:
            dt = pd.to_datetime(f"{date_dt.strftime('%b %d, %Y')} {time_str}", format="%b %d, %Y %I:%M %p")
            if dt < ref_dt:
                dt += timedelta(days=1)
            return dt
        except:
            return pd.NaT

    df['DateTime_In'] = df.apply(lambda row: parse_dt(row['Date'], row['Time In']), axis=1)
    
    cols_to_numeric = ['Total Hours', 'Regular Hours', 'Estimated Overtime', 'Break Duration']
    for col in cols_to_numeric:
        df[col] = pd.to_numeric(df.get(col, 0), errors='coerce').fillna(0)

    # --- Agrupación ---
    grouped = df.groupby(['Employee', 'Date'])
    violations = []

    total_groups = len(grouped)
    processed_count = 0

    for (emp, date_str), group in grouped:
        processed_count += 1
        if progress_bar and processed_count % 10 == 0:
            progress_bar.progress(processed_count / total_groups, text="Analizando turnos...")

        total_hours = group['Total Hours'].sum()
        reg_hours = group['Regular Hours'].sum()
        ot_hours = group['Estimated Overtime'].sum()
        
        valid_starts = group['DateTime_In'].dropna()
        if valid_starts.empty:
            continue
        shift_start = valid_starts.min()
        
        valid_breaks = []
        for _, row in group.iterrows():
            if row['Break Duration'] >= min_break_hours: 
                b_start = parse_time_conditional(shift_start, row['Break Start'], shift_start)
                if pd.notna(b_start):
                    valid_breaks.append(b_start)
        valid_breaks.sort()
        
        # === NUEVA LÓGICA DE AUDITORÍA ===
        
        # 1. Chequeo de Waiver (La corrección de Tany)
        # Si trabajó 6 horas o menos, NO se requiere descanso. Saltamos validación.
        if total_hours <= waiver_limit:
            continue 

        # 2. Si trabajó > 6 horas, entramos aquí.
        # PERO la regla sigue siendo: el descanso debió ser antes de la 5ta hora.
        violation_type = None
        details = ""
        
        deadline_time = shift_start + timedelta(hours=deadline_hours) # Deadline es a la 5ta hora
            
        if not valid_breaks:
            violation_type = "Missed Meal Break"
            details = f"Turno de {total_hours:.2f}h (>6h) sin descanso registrado."
        else:
            first_break = valid_breaks[0]
            if first_break > deadline_time:
                violation_type = "Late Meal Break"
                break_str = first_break.strftime('%I:%M %p')
                limit_str = deadline_time.strftime('%I:%M %p')
                details = f"Descanso tarde a las {break_str}. Debió ser antes de las {limit_str} (Hr 5)."

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
        
        # Regla 2da Comida (> 10 horas)
        if total_hours > 10.0:
            deadline_10th = shift_start + timedelta(hours=10)
            if len(valid_breaks) < 2:
                waiver_status = "(Waivable)" if total_hours <= 12.0 else "(NON-Waivable)"
                violations.append({
                    "Nombre": emp,
                    "Date": date_str,
                    "Regular Hours": round(reg_hours, 2),
                    "Overtime Hours": round(ot_hours, 2),
                    "Total Horas Día": round(total_hours, 2),
                    "Violación": "Missing 2nd Meal",
                    "Detalles": f"Turno > 10h. Solo {len(valid_breaks)} descanso(s). {waiver_status}"
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

st.sidebar.title("Menú Principal")
menu = st.sidebar.radio("Navegación", ("Dashboard", "Configuración"))

st.markdown("""
    <style>
    body { background-color: #f4f6f9; }
    .metric-card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); text-align: center; }
    .card-title { font-size: 16px; color: #6c757d; }
    .card-value { font-size: 28px; font-weight: bold; color: #2c3e50; }
    </style>
""", unsafe_allow_html=True)

if menu == "Dashboard":
    st.markdown(f"""
        <h2 style='text-align: center;'>🛡️ Auditoría de Tiempos Toast</h2>
        <div style='text-align: center; color: gray; font-size: 0.9em; margin-bottom: 20px;'>
            <b>Regla Activa:</b> Turnos ≤ {st.session_state['waiver_limit_hours']}h no requieren descanso. <br>
            Si > {st.session_state['waiver_limit_hours']}h, descanso obligatorio antes de la hora {st.session_state['meal_deadline_hours']}.
        </div>
    """, unsafe_allow_html=True)

    file = st.file_uploader("Arrastra tu archivo CSV de Toast aquí", type=["csv"])

    if file:
        progress_bar = st.progress(0, text="Leyendo archivo...")
        min_break_hours = st.session_state['min_break_minutes'] / 60.0
        
        violations_df = process_csv_toast(
            file, 
            deadline_hours=st.session_state['meal_deadline_hours'],
            waiver_limit=st.session_state['waiver_limit_hours'],
            min_break_hours=min_break_hours,
            progress_bar=progress_bar
        )
        progress_bar.empty()

        if not violations_df.empty:
            st.success(f'✅ Análisis completado. Se encontraron {len(violations_df)} posibles violaciones.')
            
            col1, col2, col3 = st.columns(3)
            with col1: st.markdown(f"""<div class="metric-card"><div class="card-title">Total Incidencias</div><div class="card-value">{len(violations_df)}</div></div>""", unsafe_allow_html=True)
            with col2: st.markdown(f"""<div class="metric-card"><div class="card-title">Empleados Afectados</div><div class="card-value">{violations_df['Nombre'].nunique()}</div></div>""", unsafe_allow_html=True)
            with col3: st.markdown(f"""<div class="metric-card"><div class="card-title">Late Breaks</div><div class="card-value">{len(violations_df[violations_df['Violación'].str.contains('Late')])}</div></div>""", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 📊 Resumen Ejecutivo por Empleado")
            summary_df = violations_df.groupby(['Nombre', 'Violación']).size().unstack(fill_value=0)
            summary_df['Total Violaciones'] = summary_df.sum(axis=1)
            summary_df = summary_df.sort_values('Total Violaciones', ascending=False).reset_index()
            
            col_tbl, col_cht = st.columns([1.5, 1])
            with col_tbl:
                st.dataframe(summary_df, use_container_width=True)
                csv_sum = summary_df.to_csv(index=False).encode('utf-8')
                st.download_button("⬇️ Descargar Resumen (CSV)", data=csv_sum, file_name="resumen_empleados.csv", mime="text/csv")
            with col_cht:
                 chart = alt.Chart(summary_df).mark_bar(color="#ff6b6b").encode(
                    x=alt.X('Total Violaciones', title='Cantidad'), y=alt.Y('Nombre', sort='-x', title=''), tooltip=['Nombre', 'Total Violaciones']
                ).properties(height=350)
                 st.altair_chart(chart, use_container_width=True)

            st.markdown("---")
            st.markdown("### 📋 Detalle de Incidencias")
            st.dataframe(violations_df.style.applymap(lambda x: 'color: red; font-weight: bold' if 'Missing' in str(x) else ('color: orange' if 'Late' in str(x) else ''), subset=['Violación']), use_container_width=True)
            csv_full = violations_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Descargar Detalle (CSV)", data=csv_full, file_name="detalle_meal_break.csv", mime="text/csv")
        else:
            st.balloons()
            st.success("🎉 ¡Excelente! No se encontraron violaciones bajo las reglas actuales.")

elif menu == "Configuración":
    st.header("⚙️ Configuración de Reglas")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Reglas de Tiempo")
        new_waiver = st.number_input("Límite de horas para exentar descanso (Waiver)", 4.0, 8.0, st.session_state['waiver_limit_hours'], 0.5)
        new_deadline = st.number_input("Si se excede el límite, el descanso debe ser antes de la hora:", 4.0, 6.0, st.session_state['meal_deadline_hours'], 0.5)
        new_min_break = st.number_input("Duración mínima del descanso (Minutos)", 10, 60, int(st.session_state['min_break_minutes']), 5)
        
        if st.button("💾 Guardar Cambios"):
            st.session_state['waiver_limit_hours'] = new_waiver
            st.session_state['meal_deadline_hours'] = new_deadline
            st.session_state['min_break_minutes'] = new_min_break
            st.success("Reglas actualizadas.")

    with col2:
        st.info(f"""
        **Lógica Actual:**
        1. Si el turno dura **≤ {st.session_state['waiver_limit_hours']} horas**, NO se requiere descanso.
        2. Si el turno dura **> {st.session_state['waiver_limit_hours']} horas**, es obligatorio.
        3. Si es obligatorio, debe iniciar antes de la **hora {st.session_state['meal_deadline_hours']}**.
        """)
