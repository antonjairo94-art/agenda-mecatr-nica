import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="Agenda Mecatrónica", page_icon="⚙️", layout="centered")

# ==========================================
# TRADUCCIÓN Y FORMATO DE FECHAS EN ESPAÑOL
# ==========================================
DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def format_date_spanish(d):
    return f"{DIAS_SEMANA[d.weekday()]} {d.day:02d} de {MESES[d.month-1]} del {d.year}"

def format_date_short(d):
    return f"{d.day:02d}/{d.month:02d}/{d.year}"

# ==========================================
# CONFIGURACIÓN DE BASE Y ROTACIÓN
# ==========================================
START_DATE = datetime(2026, 9, 2).date()

SHIFTS = {
    0: {"name": "Turno Mañana (07:00 - 15:00)", "type": "M", "free_hrs_weekday": 2.5, "free_hrs_weekend": 6.0},
    1: {"name": "Turno Tarde (15:00 - 23:00)",  "type": "T", "free_hrs_weekday": 4.5, "free_hrs_weekend": 5.0},
    2: {"name": "Turno Noche (23:00 - 07:00)",  "type": "N", "free_hrs_weekday": 2.5, "free_hrs_weekend": 4.0},
    3: {"name": "Día de Descanso",             "type": "D", "free_hrs_weekday": 6.0, "free_hrs_weekend": 10.0}
}

CLASSES = {
    0: [("13:50 - 15:30", "Manufactura"), ("15:40 - 17:20", "Diseño"), ("17:30 - 19:10", "Automatización")],
    1: [("13:50 - 15:30", "Manufactura"), ("15:40 - 17:20", "Robótica"), ("17:30 - 19:10", "Automatización")],
    2: [],
    3: [("13:50 - 15:30", "Mantenimiento"), ("17:30 - 19:10", "Robótica")],
    4: [("13:50 - 15:30", "Mantenimiento"), ("17:30 - 19:10", "Robótica")],
    5: [],
    6: []
}

if "agenda_db" not in st.session_state:
    st.session_state.agenda_db = []

if "busqueda_temp" not in st.session_state:
    st.session_state.busqueda_temp = None

if "fecha_diaria" not in st.session_state:
    st.session_state.fecha_diaria = datetime.now().date()

# ==========================================
# FUNCIONES DE LÓGICA
# ==========================================
def get_shift_info(target_date):
    delta_days = (target_date - START_DATE).days
    shift_idx = delta_days % 4
    return SHIFTS[shift_idx], shift_idx

def get_day_classes(target_date):
    weekday = target_date.weekday()
    return CLASSES.get(weekday, [])

def evaluate_class_attendance(shift_idx, class_start):
    if shift_idx == 1:
        return "🔴 FALTA TOTAL (Cruce laboral)"
    elif shift_idx == 0 and class_start == "13:50 - 15:30":
        return "🟡 NO LLEGAS (Sales 3pm de Sechura)"
    elif shift_idx == 0 and class_start == "15:40 - 17:20":
        return "🟡 LLEGAS PARCIAL (~4:30 PM a Piura)"
    else:
        return "🟢 ASISTES NORMAL"

def calculate_free_hours(target_date):
    shift, shift_idx = get_shift_info(target_date)
    is_weekend = target_date.weekday() >= 5
    base_free = shift["free_hrs_weekend"] if is_weekend else shift["free_hrs_weekday"]
    agendado = sum(item['duracion'] for item in st.session_state.agenda_db if item['fecha'] == target_date and item.get('estado') == 'Pendiente')
    return max(0.0, base_free - agendado)

# ==========================================
# INTERFAZ DE USUARIO (MÓVIL)
# ==========================================
st.title("⚙️ Mi Agenda Mecatrónica")
st.caption("Control de Turnos, Clases, Trabajos de U y Reparaciones")

menu = st.sidebar.radio("Navegación", ["📅 Vista Diario / Hoy", "🔍 Agendar Reparación (Buscador)", "🎓 Tareas de Universidad", "📋 Lista de Pendientes"])

# Restablece la fecha automáticamente a HOY si cambias de pestaña y vuelves al inicio
if "last_menu" not in st.session_state:
    st.session_state.last_menu = menu

if menu != st.session_state.last_menu:
    if menu == "📅 Vista Diario / Hoy":
        st.session_state.fecha_diaria = datetime.now().date()
    st.session_state.last_menu = menu

# ------------------------------------------
# OPCIÓN 1: VISTA DIARIO / HOY
# ------------------------------------------
if menu == "📅 Vista Diario / Hoy":
    st.subheader("📅 Consulta Diaria")
    
    selected_date = st.date_input("Selecciona una fecha:", st.session_state.fecha_diaria, format="DD/MM/YYYY")
    st.session_state.fecha_diaria = selected_date
    
    st.markdown(f"**Fecha:** {format_date_spanish(selected_date)} ({format_date_short(selected_date)})")
    
    shift_info, shift_idx = get_shift_info(selected_date)
    day_classes = get_day_classes(selected_date)
    free_hrs = calculate_free_hours(selected_date)
    
    st.info(f"💼 **Trabajo:** {shift_info['name']}")
    st.success(f"⏳ **Horas Libres Disponibles:** {free_hrs} horas útiles")
    
    st.markdown("### 🎓 Clases en Piura")
    if not day_classes:
        st.write("No tienes clases programadas este día.")
    else:
        for hor, curso in day_classes:
            estado = evaluate_class_attendance(shift_idx, hor)
            st.write(f"• **{curso}** ({hor}): {estado}")
            
    st.markdown("### 🛠️ Reparaciones y Tareas para este día")
    actividades = [x for x in st.session_state.agenda_db if x['fecha'] == selected_date and x.get('estado') == 'Pendiente']
    if not actividades:
        st.caption("No hay tareas ni reparaciones agendadas para hoy.")
    else:
        for act in actividades:
            tipo_icon = "🛠️" if act['tipo'] == "Reparación" else "🎓"
            precio_info = f" | Cobro: S/. {act.get('precio', 0.0):.2f}" if act['tipo'] == "Reparación" else ""
            st.warning(f"{tipo_icon} **{act['titulo']}** ({act['duracion']} hrs){precio_info} - Entrega: {format_date_short(act['fecha_entrega'])}")

# ------------------------------------------
# OPCIÓN 2: BUSCADOR DE HUECOS LIBRES
# ------------------------------------------
elif menu == "🔍 Agendar Reparación (Buscador)":
    st.subheader("🔍 Asistente de Disponibilidad")
    st.write("Encuentra automáticamente el día más cercano con horas libres suficientes.")
    
    with st.form("form_reparacion"):
        cliente = st.text_input("Cliente / Nombre del trabajo:", placeholder="Ej. Impresora Epson L3110")
        precio_cobro = st.number_input("Precio a cobrar (S/.):", min_value=0.0, value=0.0, step=5.0)
        duracion_req = st.number_input("Horas estimadas de trabajo:", min_value=0.5, max_value=8.0, value=2.0, step=0.5)
        dias_max = st.slider("Buscar dentro de los próximos (días):", 1, 30, 14)
        submitted = st.form_submit_button("🔎 Buscar Día Libre Más Cercano")
        
    if submitted:
        today = datetime.now().date()
        encontrado = None
        
        for i in range(dias_max):
            eval_date = today + timedelta(days=i)
            hrs_disp = calculate_free_hours(eval_date)
            if hrs_disp >= duracion_req:
                encontrado = eval_date
                break
                
        if encontrado:
            st.session_state.busqueda_temp = {
                "cliente": cliente,
                "precio": precio_cobro,
                "duracion": duracion_req,
                "fecha": encontrado
            }
        else:
            st.session_state.busqueda_temp = None
            st.error("❌ No se encontró ningún día con tantas horas libres continuas en el rango seleccionado.")

    if st.session_state.busqueda_temp:
        res = st.session_state.busqueda_temp
        shift_f, _ = get_shift_info(res["fecha"])
        st.divider()
        st.success("🎯 **¡Día libre encontrado!**")
        st.write(f"• **Fecha:** {format_date_spanish(res['fecha'])} ({format_date_short(res['fecha'])})")
        st.write(f"• **Turno de trabajo ese día:** {shift_f['name']}")
        st.write(f"• **Horas libres disponibles:** {calculate_free_hours(res['fecha'])} hrs")
        
        if st.button("✅ Confirmar y Agendar Reparación"):
            st.session_state.agenda_db.append({
                "tipo": "Reparación",
                "titulo": f"Reparación: {res['cliente']}",
                "fecha": res['fecha'],
                "fecha_entrega": res['fecha'] + timedelta(days=1),
                "duracion": res['duracion'],
                "precio": res['precio'],
                "estado": "Pendiente"
            })
            st.session_state.busqueda_temp = None
            st.balloons()
            st.success("¡Agendado exitosamente!")
            st.rerun()

# ------------------------------------------
# OPCIÓN 3: TAREAS DE UNIVERSIDAD
# ------------------------------------------
elif menu == "🎓 Tareas de Universidad":
    st.subheader("🎓 Programar Trabajo / Proyecto de U")
    
    with st.form("form_u"):
        titulo_u = st.text_input("Nombre del trabajo/proyecto:", placeholder="Ej. Informe de Lab Robótica")
        fecha_entrega = st.date_input("Fecha límite de entrega:", datetime.now().date() + timedelta(days=3), format="DD/MM/YYYY")
        hrs_u = st.number_input("Horas de dedicación requeridas:", min_value=0.5, value=2.0)
        submit_u = st.form_submit_button("📌 Registrar Tarea")
        
    if submit_u:
        fecha_trabajo = fecha_entrega - timedelta(days=1)
        st.session_state.agenda_db.append({
            "tipo": "Universidad",
            "titulo": titulo_u,
            "fecha": fecha_trabajo,
            "fecha_entrega": fecha_entrega,
            "duracion": hrs_u,
            "precio": 0.0,
            "estado": "Pendiente"
        })
        st.success(f"Tarea registrada. Programada para avanzar el {format_date_short(fecha_trabajo)} (un día antes de la entrega).")

# ------------------------------------------
# OPCIÓN 4: LISTA DE PENDIENTES
# ------------------------------------------
elif menu == "📋 Lista de Pendientes":
    st.subheader("📋 Estado de Entregas y Alertas")
    
    ganancias_totales = sum(item.get('precio', 0.0) for item in st.session_state.agenda_db if item.get('estado') == 'Completado' and item['tipo'] == 'Reparación')
    st.metric("💰 Ganancias Acumuladas (Reparaciones Entregadas)", f"S/. {ganancias_totales:.2f}")
    
    st.divider()
    
    pendientes = [item for item in st.session_state.agenda_db if item.get('estado', 'Pendiente') == 'Pendiente']
    
    if not pendientes:
        st.info("No hay compromisos o reparaciones pendientes agendados.")
    else:
        today = datetime.now().date()
        for idx, item in enumerate(st.session_state.agenda_db):
            if item.get('estado', 'Pendiente') == 'Pendiente':
                dias_faltantes = (item['fecha_entrega'] - today).days
                
                if dias_faltantes < 0:
                    alerta = "🔴 VENCIDO"
                elif dias_faltantes <= 2:
                    alerta = f"🚨 ENTREGAR EN {dias_faltantes} DÍAS"
                else:
                    alerta = f"🟢 Faltan {dias_faltantes} días"
                    
                col1, col2, col3 = st.columns([2.5, 1, 1])
                with col1:
                    precio_str = f" | S/. {item.get('precio', 0.0):.2f}" if item['tipo'] == 'Reparación' else ""
                    st.write(f"**{item['titulo']}** [{item['tipo']}{precio_str}]")
                    st.caption(f"Trabajo: {format_date_short(item['fecha'])} | Entrega: {format_date_short(item['fecha_entrega'])} | {alerta}")
                with col2:
                    if st.button("✅ Listo / OK", key=f"ok_{idx}"):
                        item['estado'] = 'Completado'
                        st.rerun()
                with col3:
                    if st.button("Eliminar", key=f"del_{idx}"):
                        st.session_state.agenda_db.pop(idx)
                        st.rerun()

```
