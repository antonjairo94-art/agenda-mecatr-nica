import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

st.set_page_config(page_title="Agenda & Taller Mecatrónico", page_icon="🛠️", layout="centered")

# --- CONFIGURACIÓN DE ROTACIÓN Y HORARIOS ---
START_DATE = datetime(2026, 9, 2).date() # Sep 02 = Turno Mañana (07:00 - 15:00)

SHIFTS = {
    0: {"name": "Turno Mañana (07:00 - 15:00)", "type": "M", "free_hrs_weekday": 2.5, "free_hrs_weekend": 6.0},
    1: {"name": "Turno Tarde (15:00 - 23:00)",  "type": "T", "free_hrs_weekday": 4.5, "free_hrs_weekend": 5.0},
    2: {"name": "Turno Noche (23:00 - 07:00)",  "type": "N", "free_hrs_weekday": 2.5, "free_hrs_weekend": 4.0},
    3: {"name": "Día de Descanso",             "type": "D", "free_hrs_weekday": 6.0, "free_hrs_weekend": 10.0}
}

# Horarios lectivos (0: Lunes, 1: Martes, 2: Miércoles, 3: Jueves, 4: Viernes)
CLASSES = {
    0: [("13:50 - 15:30", "Manufactura"), ("15:40 - 17:20", "Diseño"), ("17:30 - 19:10", "Automatización")],
    1: [("13:50 - 15:30", "Manufactura"), ("15:40 - 17:20", "Robótica"), ("17:30 - 19:10", "Automatización")], # Robótica añadida los martes
    2: [],
    3: [("13:50 - 15:30", "Mantenimiento"), ("17:30 - 19:10", "Robótica")],
    4: [("13:50 - 15:30", "Mantenimiento"), ("17:30 - 19:10", "Robótica")],
    5: [],
    6: []
}

DIAS_SEMANA = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# --- FUNCIONES DE LÓGICA DE ROTACIÓN ---
def get_shift_info(target_date):
    delta_days = (target_date - START_DATE).days
    shift_idx = delta_days % 4
    return SHIFTS[shift_idx], shift_idx

def evaluate_class_attendance(shift_idx, class_start):
    if shift_idx == 1: # Turno Tarde
        return "🔴 FALTA TOTAL (Cruce laboral)"
    elif shift_idx == 0 and "13:50" in class_start:
        return "🟡 NO LLEGAS (Sales 3pm de Sechura)"
    elif shift_idx == 0 and "15:40" in class_start:
        return "🟡 LLEGAS PARCIAL (~4:30 PM a Piura)"
    else:
        return "🟢 ASISTES NORMAL"

# --- INICIALIZAR MEMORIA DE REPARACIONES ---
if "reparaciones" not in st.session_state:
    st.session_state.reparaciones = []

# --- ENCABEZADO Y FECHA ---
ahora = datetime.now()
nombre_dia = DIAS_SEMANA[ahora.weekday()]
num_dia = ahora.day
nombre_mes = MESES[ahora.month - 1]
anio = ahora.year

fecha_larga = f"{nombre_dia} {num_dia} de {nombre_mes} del {anio}"
fecha_corta = f"{num_dia:02d}/{ahora.month:02d}/{anio}"

st.title("🛠️ Agenda & Taller Mecatrónico")
st.subheader(f"📅 Hoy: {fecha_larga}")
st.divider()

# --- PESTAÑAS PRINCIPALES ---
tab1, tab2 = st.tabs(["⏰ Horario y Turnos", "📋 Control de Reparaciones"])

# ==========================================
# PESTAÑA 1: HORARIOS Y COINCIDENCIAS
# ==========================================
with tab1:
    st.header("Consulta de Turno y Clases")
    selected_date = st.date_input("Seleccionar fecha a consultar:", ahora.date())
    
    sel_weekday = selected_date.weekday()
    sel_nombre_dia = DIAS_SEMANA[sel_weekday]
    shift_info, shift_idx = get_shift_info(selected_date)
    day_classes = CLASSES.get(sel_weekday, [])
    
    st.info(f"💼 **Trabajo:** {shift_info['name']}")
    
    st.markdown(f"### 🎓 Clases del {sel_nombre_dia}")
    if not day_classes:
        st.write("No tienes clases programadas para este día.")
    else:
        for hor, curso in day_classes:
            estado = evaluate_class_attendance(shift_idx, hor)
            st.write(f"• **{curso}** ({hor}): {estado}")

# ==========================================
# PESTAÑA 2: REPARACIONES Y GANANCIAS
# ==========================================
with tab2:
    st.header("Gestionar Pedidos de Taller")
    
    with st.form("nuevo_pedido", clear_on_submit=True):
        st.subheader("➕ Registrar Nuevo Trabajo")
        col_c, col_e, col_p = st.columns([2, 2, 1])
        with col_c:
            cliente = st.text_input("Nombre del Cliente")
        with col_e:
            equipo = st.text_input("Equipo / Artefacto")
        with col_p:
            precio = st.number_input("Precio (S/.)", min_value=0.0, step=5.0)
            
        btn_guardar = st.form_submit_button("Guardar Pedido")
        
        if btn_guardar:
            if cliente and equipo:
                nuevo_item = {
                    "id": len(st.session_state.reparaciones) + 1,
                    "cliente": cliente,
                    "equipo": equipo,
                    "precio": precio,
                    "estado": "Pendiente",
                    "fecha": fecha_corta
                }
                st.session_state.reparaciones.append(nuevo_item)
                st.success(f"¡Pedido registrado correctamente!")
            else:
                st.warning("Completa el cliente y el equipo.")

    st.divider()

    completados = [r for r in st.session_state.reparaciones if r["estado"] == "Entregado"]
    total_ganancias = sum(r["precio"] for r in completados)
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("💰 Ganancia Acumulada", f"S/. {total_ganancias:.2f}")
    col_m2.metric("📦 Entregados", f"{len(completados)}")

    st.divider()
    st.subheader("⏳ Reparaciones Pendientes")
    pendientes = [r for r in st.session_state.reparaciones if r["estado"] == "Pendiente"]

    if not pendientes:
        st.info("Sin reparaciones pendientes.")
    else:
        for item in pendientes:
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.markdown(f"**{item['equipo']}** - *{item['cliente']}* | **S/. {item['precio']:.2f}** ({item['fecha']})")
            with col_btn:
                if st.button("✅ Listo / OK", key=f"btn_{item['id']}"):
                    for r in st.session_state.reparaciones:
                        if r["id"] == item["id"]:
                            r["estado"] = "Entregado"
                    st.rerun()
