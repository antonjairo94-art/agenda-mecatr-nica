import streamlit as st
from datetime import datetime, timedelta
import json
import os

st.set_page_config(page_title="Agenda Mecatrónica", page_icon="⚙️", layout="centered")

DATA_FILE = "agenda_data.json"

# TIEMPOS DE VIAJE FIJOS (en minutos)
VIAJE_IDA = 135    # 2 horas 15 minutos (Sechura ➔ Piura)
VIAJE_VUELTA = 180 # 3 horas (Piura ➔ Sechura)

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre"]

def format_date_spanish(d):
    return f"{DIAS_SEMANA[d.weekday()]} {d.day:02d} de {MESES[d.month-1]} del {d.year}"

def format_date_short(d):
    return f"{d.day:02d}/{d.month:02d}/{d.year}"

# ==========================================
# CONFIGURACIÓN DE BASE Y ROTACIÓN
# ==========================================
START_DATE = datetime(2026, 9, 2).date()

# Minutos desde medianoche
SHIFTS = {
    0: {"name": "Turno Mañana", "start": 7*60,  "end": 15*60},
    1: {"name": "Turno Tarde",  "start": 15*60, "end": 23*60},
    2: {"name": "Turno Noche",  "start": 23*60, "end": 24*60},
    3: {"name": "Descanso",      "start": None,  "end": None},
}

# Horario real de clases (minutos desde medianoche: Ej. 830 = 13:50, 930 = 15:30)
CLASSES = {
    0: [(830, 930, "Manufactura"), (940, 1040, "Diseño"), (1050, 1150, "Automatización")],
    1: [(830, 930, "Manufactura"), (940, 1040, "Robótica"), (1050, 1150, "Automatización")],
    2: [],
    3: [(830, 930, "Mantenimiento"), (1050, 1150, "Robótica")],
    4: [(830, 930, "Mantenimiento"), (1050, 1150, "Robótica")],
    5: [],
    6: [],
}

def hhmm(m):
    h, mm = divmod(int(m), 60)
    ampm = "pm" if h >= 12 else "am"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    return f"{h12}:{mm:02d}{ampm}"

# ==========================================
# PERSISTENCIA (archivo JSON local)
# ==========================================
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            for item in raw:
                item["fecha"] = datetime.strptime(item["fecha"], "%Y-%m-%d").date()
                item["fecha_entrega"] = datetime.strptime(item["fecha_entrega"], "%Y-%m-%d").date()
            return raw
        except Exception:
            return []
    return []

def save_data(data):
    serializable = []
    for item in data:
        it = dict(item)
        it["fecha"] = it["fecha"].strftime("%Y-%m-%d")
        it["fecha_entrega"] = it["fecha_entrega"].strftime("%Y-%m-%d")
        serializable.append(it)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(serializable, f, ensure_ascii=False, indent=2)

if "agenda_db" not in st.session_state:
    st.session_state.agenda_db = load_data()

if "busqueda_temp" not in st.session_state:
    st.session_state.busqueda_temp = None

if "fecha_diaria" not in st.session_state:
    st.session_state.fecha_diaria = datetime.now().date()

# ==========================================
# LÓGICA DE HORARIO Y TIEMPOS REALES
# ==========================================
def get_shift_info(target_date):
    delta_days = (target_date - START_DATE).days
    shift_idx = delta_days % 4
    return SHIFTS[shift_idx], shift_idx

def build_day_minutes(target_date):
    """Devuelve un array de 1440 minutos etiquetados con la disponibilidad real."""
    minutes = ["libre"] * 1440
    shift, shift_idx = get_shift_info(target_date)

    if shift_idx == 0:
        for m in range(7*60, 15*60): minutes[m] = "turno"
    elif shift_idx == 1:
        for m in range(15*60, 23*60): minutes[m] = "turno"
    elif shift_idx == 2:
        for m in range(23*60, 24*60): minutes[m] = "turno"
    elif shift_idx == 3:
        for m in range(0, 7*60): minutes[m] = "turno"

    classes = CLASSES.get(target_date.weekday(), [])
    if classes:
        first_s = classes[0][0]
        last_e = classes[-1][1]
        
        # Bloquea todo el tiempo de ausencia considerando el viaje real Sechura <-> Piura
        start_ausencia = max(0, first_s - VIAJE_IDA)
        end_ausencia = min(1440, last_e + VIAJE_VUELTA)
        
        for m in range(start_ausencia, end_ausencia):
            if minutes[m] == "turno":
                minutes[m] = "ambos"
            else:
                minutes[m] = "clase_o_viaje"

    return minutes

def get_day_classes(target_date):
    return CLASSES.get(target_date.weekday(), [])

def evaluate_class_attendance(target_date, class_start, class_end):
    """Evalúa si puedes asistir a clases tomando en cuenta el turno y el viaje real."""
    shift, shift_idx = get_shift_info(target_date)
    if shift_idx == 3: 
        return "🟢 ASISTES NORMAL"
        
    shift_s = SHIFTS[shift_idx]["start"]
    shift_e = SHIFTS[shift_idx]["end"]
    
    # Ventana bloqueada en Piura por cruce con trabajo o tiempos de viaje
    piura_bloqueado_inicio = shift_s - VIAJE_VUELTA
    piura_bloqueado_fin = shift_e + VIAJE_IDA
    
    cruce = max(0, min(class_end, piura_bloqueado_fin) - max(class_start, piura_bloqueado_inicio))
    duracion_clase = class_end - class_start
    
    if cruce == 0:
        return "🟢 ASISTES NORMAL"
    elif cruce == duracion_clase:
        return "🔴 FALTA TOTAL (Cruce con trabajo o viaje)"
    else:
        pct = round(100 * (duracion_clase - cruce) / duracion_clase)
        return f"🟡 ASISTES PARCIAL (~{pct}% de la clase)"

def calculate_free_hours(target_date, exclude_id=None):
    minutes = build_day_minutes(target_date)
    free_minutes = sum(1 for x in minutes if x == "libre")
    base_free = free_minutes / 60.0
    agendado = sum(
        item["duracion"] for item in st.session_state.agenda_db
        if item["fecha"] == target_date and item.get("estado") == "Pendiente"
        and item.get("id") != exclude_id
    )
    return round(max(0.0, base_free - agendado), 1)

def buscar_dias_libres(duracion_req, dias_max, hasta_fecha=None):
    today = datetime.now().date()
    candidatos = []
    limite = dias_max
    if hasta_fecha:
        limite = min(dias_max, max(1, (hasta_fecha - today).days))
    for i in range(limite + 1):
        d = today + timedelta(days=i)
        libres = calculate_free_hours(d)
        if libres >= duracion_req:
            candidatos.append((d, libres))
    candidatos.sort(key=lambda x: -x[1])
    return candidatos[:3]

# ==========================================
# INTERFAZ DE USUARIO (MÓVIL)
# ==========================================
st.title("⚙️ Mi Agenda Mecatrónica")
st.caption("Control de Turnos, Clases, Trabajos de U y Reparaciones")

menu = st.sidebar.radio("Navegación", [
    "📅 Vista Diario / Hoy",
    "🔍 Agendar Reparación (Buscador)",
    "🎓 Tareas de Universidad",
    "📋 Lista de Pendientes"
])

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

    if shift_idx in (0, 1, 2):
        horario_txt = f"{hhmm(SHIFTS[shift_idx]['start'])} - {hhmm(SHIFTS[shift_idx]['end'] % 1440 or 1440)}"
        st.info(f"💼 **Trabajo:** {shift_info['name']} ({horario_txt})")
    else:
        st.info(f"💼 **Trabajo:** {shift_info['name']} (libre)")

    st.success(f"⏳ **Horas Libres Disponibles:** {free_hrs} horas")

    st.markdown("### 🎓 Clases en Piura")
    if not day_classes:
        st.write("No tienes clases programadas este día.")
    else:
        for s, e, curso in day_classes:
            estado = evaluate_class_attendance(selected_date, s, e)
            st.write(f"• **{curso}** ({hhmm(s)} - {hhmm(e)}): {estado}")

    st.markdown("### 🛠️ Reparaciones y Tareas para este día")
    actividades = [x for x in st.session_state.agenda_db
                   if x["fecha"] == selected_date and x.get("estado") == "Pendiente"]
    if not actividades:
        st.caption("No hay tareas ni reparaciones agendadas para hoy.")
    else:
        for act in actividades:
            tipo_icon = "🛠️" if act["tipo"] == "Reparación" else "🎓"
            precio_info = f" | Cobro: S/. {act.get('precio', 0.0):.2f}" if act["tipo"] == "Reparación" else ""
            st.warning(f"{tipo_icon} **{act['titulo']}** ({act['duracion']} hrs){precio_info} "
                       f"- Entrega: {format_date_short(act['fecha_entrega'])}")

# ------------------------------------------
# OPCIÓN 2: BUSCADOR DE HUECOS LIBRES
# ------------------------------------------
elif menu == "🔍 Agendar Reparación (Buscador)":
    st.subheader("🔍 Asistente de Disponibilidad")
    st.write("Encuentra automáticamente los días más cercanos con horas libres suficientes.")

    with st.form("form_reparacion"):
        cliente = st.text_input("Cliente / Nombre del trabajo:", placeholder="Ej. Impresora Epson L3110")
        precio_cobro = st.number_input("Precio a cobrar (S/.):", min_value=0.0, value=0.0, step=5.0)
        duracion_req = st.number_input("Horas estimadas de trabajo:", min_value=0.5, max_value=12.0, value=2.0, step=0.5)
        dias_max = st.slider("Buscar dentro de los próximos (días):", 1, 45, 14)
        fecha_entrega_deseada = st.date_input(
            "Fecha de entrega al cliente:",
            datetime.now().date() + timedelta(days=3), format="DD/MM/YYYY"
        )
        submitted = st.form_submit_button("🔎 Buscar Mejores Días")

    if submitted:
        candidatos = buscar_dias_libres(duracion_req, dias_max, hasta_fecha=fecha_entrega_deseada)
        if candidatos:
            st.session_state.busqueda_temp = {
                "cliente": cliente, "precio": precio_cobro, "duracion": duracion_req,
                "fecha_entrega": fecha_entrega_deseada, "candidatos": candidatos,
            }
        else:
            st.session_state.busqueda_temp = None
            st.error("❌ No se encontró ningún día con suficientes horas libres en ese rango.")

    if st.session_state.busqueda_temp:
        res = st.session_state.busqueda_temp
        st.divider()
        st.success("🎯 **Días disponibles encontrados:**")
        for idx, (fecha_c, libres_c) in enumerate(res["candidatos"]):
            shift_f, _ = get_shift_info(fecha_c)
            with st.container(border=True):
                st.write(f"**{format_date_spanish(fecha_c)}**")
                st.caption(f"Turno: {shift_f['name']} · Horas libres: {libres_c}h")
                if st.button(f"✅ Agendar aquí", key=f"pick_{idx}"):
                    st.session_state.agenda_db.append({
                        "id": f"r{datetime.now().timestamp()}",
                        "tipo": "Reparación",
                        "titulo": f"Reparación: {res['cliente']}",
                        "fecha": fecha_c,
                        "fecha_entrega": res["fecha_entrega"],
                        "duracion": res["duracion"],
                        "precio": res["precio"],
                        "estado": "Pendiente",
                    })
                    save_data(st.session_state.agenda_db)
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
        submit_u = st.form_submit_button("🔎 Buscar mejor día y registrar")

    if submit_u:
        candidatos = buscar_dias_libres(hrs_u, dias_max=45, hasta_fecha=fecha_entrega)
        if candidatos:
            mejor_fecha, libres = candidatos[0]
            st.session_state.agenda_db.append({
                "id": f"u{datetime.now().timestamp()}",
                "tipo": "Universidad",
                "titulo": titulo_u,
                "fecha": mejor_fecha,
                "fecha_entrega": fecha_entrega,
                "duracion": hrs_u,
                "precio": 0.0,
                "estado": "Pendiente",
            })
            save_data(st.session_state.agenda_db)
            st.success(f"Tarea registrada. Mejor día encontrado para avanzarla: "
                       f"{format_date_spanish(mejor_fecha)} ({libres}h libres).")
        else:
            st.error("❌ No hay ningún día antes de la entrega con suficientes horas libres.")

# ------------------------------------------
# OPCIÓN 4: LISTA DE PENDIENTES
# ------------------------------------------
elif menu == "📋 Lista de Pendientes":
    st.subheader("📋 Estado de Entregas y Alertas")

    ganancias_totales = sum(
        item.get("precio", 0.0) for item in st.session_state.agenda_db
        if item.get("estado") == "Completado" and item["tipo"] == "Reparación"
    )
    st.metric("💰 Ganancias Acumuladas (Reparaciones Entregadas)", f"S/. {ganancias_totales:.2f}")

    st.divider()

    pendientes = [item for item in st.session_state.agenda_db if item.get("estado", "Pendiente") == "Pendiente"]

    if not pendientes:
        st.info("No hay compromisos o reparaciones pendientes agendados.")
    else:
        today = datetime.now().date()
        for idx, item in enumerate(st.session_state.agenda_db):
            if item.get("estado", "Pendiente") == "Pendiente":
                dias_faltantes = (item["fecha_entrega"] - today).days
                if dias_faltantes < 0:
                    alerta = "🔴 VENCIDO"
                elif dias_faltantes <= 2:
                    alerta = f"🚨 ENTREGAR EN {dias_faltantes} DÍAS"
                else:
                    alerta = f"🟢 Faltan {dias_faltantes} días"

                col1, col2, col3 = st.columns([2.5, 1, 1])
                with col1:
                    precio_str = f" | S/. {item.get('precio', 0.0):.2f}" if item["tipo"] == "Reparación" else ""
                    st.write(f"**{item['titulo']}** [{item['tipo']}{precio_str}]")
                    st.caption(f"Trabajo: {format_date_short(item['fecha'])} | "
                               f"Entrega: {format_date_short(item['fecha_entrega'])} | {alerta}")
                with col2:
                    if st.button("✅ Listo / OK", key=f"ok_{idx}"):
                        item["estado"] = "Completado"
                        save_data(st.session_state.agenda_db)
                        st.rerun()
                with col3:
                    if st.button("Eliminar", key=f"del_{idx}"):
                        st.session_state.agenda_db.pop(idx)
                        save_data(st.session_state.agenda_db)
                        st.rerun()
