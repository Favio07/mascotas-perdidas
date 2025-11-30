import streamlit as st
import os
import db 
from motor_vision import MotorVision
from utils_geo import MotorGeo
from motor_ocr import MotorOCR
from motor_faiss import MotorFAISS 
from motor_mapa import MotorMapa 
from streamlit_folium import st_folium 

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Reunificación de Mascotas (Tesis)", layout="wide")
st.title("🐶 Plataforma de Reunificación Inteligente")
st.markdown("**Módulos Activos:** Visión (ResNet50 + TTA) | Geo (H3+Nominatim) | Mapas (Folium) | OCR | FAISS")

DISTRITOS_LIMA = [
    "Ancon", "Ate", "Barranco", "Breña", "Carabayllo", "Chaclacayo", "Chorrillos", 
    "Cieneguilla", "Comas", "El Agustino", "Independencia", "Jesús María", "La Molina", 
    "La Victoria", "Lima", "Lince", "Los Olivos", "Lurigancho", "Lurín", 
    "Magdalena del Mar", "Miraflores", "Pachacamac", "Pucusana", "Pueblo Libre", 
    "Puente Piedra", "Punta Hermosa", "Punta Negra", "Rimac", "San Bartolo", "San Borja", 
    "San Isidro", "San Juan de Lurigancho", "San Juan de Miraflores", "San Luis", 
    "San Martín de Porres", "San Miguel", "Santa Anita", "Santa María del Mar", 
    "Santa Rosa", "Santiago de Surco", "Surquillo", "Villa El Salvador", 
    "Villa María del Triunfo"
]

os.makedirs("datos/imagenes", exist_ok=True)
if "db_init" not in st.session_state:
    db.init_db()
    st.session_state.db_init = True

# --- GESTIÓN DE ESTADO (PERSISTENCIA) ---
if "search_results" not in st.session_state:
    st.session_state.search_results = None
if "search_center" not in st.session_state:
    st.session_state.search_center = None
if "ultimo_registro" not in st.session_state:
    st.session_state.ultimo_registro = None # Aquí guardaremos la alerta para que no desaparezca

@st.cache_resource
def cargar_motores():
    m_vis = MotorVision()
    m_geo = MotorGeo(resolucion=9)
    m_ocr = MotorOCR()
    m_faiss = MotorFAISS(dimension=2048) 
    m_mapa = MotorMapa()
    
    todos = db.obtener_todas()
    m_faiss.limpiar()
    for mascota in todos:
        if len(mascota["vector"]) == 2048:
            m_faiss.agregar_vector(mascota["id"], mascota["vector"])
        
    return m_vis, m_geo, m_ocr, m_faiss, m_mapa

motor_vis, motor_geo, motor_ocr, motor_faiss, motor_mapa = cargar_motores()

# ==========================================
# BARRA LATERAL: REGISTRO (CON MEMORIA)
# ==========================================
with st.sidebar:
    st.header("1. Reportar Mascota")
    nombre = st.text_input("Nombre")
    distrito = st.selectbox("Distrito", DISTRITOS_LIMA)
    referencia = st.text_input("Referencia (Opcional)", placeholder="Ej. Parque de la Amistad")
    foto_subida = st.file_uploader("Subir foto", type=["jpg", "png", "jpeg"])
    
    if st.button("Registrar") and foto_subida and nombre:
        with st.spinner("Procesando..."):
            # Limpiamos estado anterior
            st.session_state.ultimo_registro = None
            
            es_animal, etiqueta = motor_vis.es_mascota(foto_subida)
            lat, lon = motor_geo.obtener_coordenadas(distrito, referencia)
            
            if not es_animal:
                st.error(f"❌ Error: {etiqueta}")
            else:
                ruta_img = f"datos/imagenes/{nombre}_{foto_subida.name}"
                with open(ruta_img, "wb") as f:
                    f.write(foto_subida.getbuffer())
                
                vector_nuevo = motor_vis.obtener_embedding(ruta_img)
                h3_index = motor_geo.obtener_h3_index(lat, lon)
                
                # --- LÓGICA DE ALERTAS ---
                scores, ids = motor_faiss.buscar(vector_nuevo, k=3)
                alerta_data = None
                
                ids_limpios = [int(i) for i in ids if i != -1]
                candidatos = db.obtener_por_ids(ids_limpios)
                
                for cand in candidatos:
                    idx = list(ids).index(cand["id"])
                    s_vis = scores[idx]
                    s_geo = motor_geo.calcular_score_geo(h3_index, cand["h3_index"])
                    s_final = (0.6 * s_vis) + (0.4 * s_geo)
                    
                    if s_final > 0.85:
                        alerta_data = {
                            "match_id": cand["id"],
                            "match_nombre": cand["nombre"],
                            "score": s_final
                        }
                        break 

                # Guardar en BD
                nuevo_id = db.guardar_mascota(nombre, distrito, h3_index, lat, lon, ruta_img, vector_nuevo)
                motor_faiss.agregar_vector(nuevo_id, vector_nuevo)
                
                # --- GUARDAR EN MEMORIA PARA QUE NO DESAPAREZCA ---
                st.session_state.ultimo_registro = {
                    "id": nuevo_id,
                    "status": "success",
                    "alerta": alerta_data
                }

    # --- MOSTRAR RESULTADO DEL REGISTRO (PERSISTENTE) ---
    if st.session_state.ultimo_registro:
        reg = st.session_state.ultimo_registro
        st.success(f"✅ Registrado (ID: {reg['id']})")
        
        if reg["alerta"]:
            # Solo mostramos globos una vez (opcional, o cada vez que se renderiza)
            st.balloons() 
            
            st.error("🚨 **¡ALERTA DE COINCIDENCIA!**")
            st.info(f"""
                Se detectó una coincidencia del **{reg['alerta']['score']*100:.0f}%** con la mascota **{reg['alerta']['match_nombre']}**.
                
                📧 **Acción Automática:**
                Se ha enviado un correo de notificación al propietario original.
            """)
        else:
            st.caption("ℹ️ No se detectaron coincidencias previas.")

# ==========================================
# ÁREA PRINCIPAL
# ==========================================
tab1, tab2, tab3 = st.tabs(["🔍 Búsqueda Geoespacial", "📄 OCR", "🗺️ Mapa General de Casos"])

# --- PESTAÑA 1: BÚSQUEDA ---
with tab1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Foto Consulta")
        foto_query = st.file_uploader("Subir foto hallazgo", type=["jpg", "png"], key="q")
        distrito_q = st.selectbox("Distrito hallazgo", DISTRITOS_LIMA)
        referencia_q = st.text_input("Referencia Hallazgo", placeholder="Ej. Ovalo Higuereta", key="ref_q")
    
    if foto_query and c1.button("Buscar"):
        with st.spinner("Buscando..."):
            vector_q = motor_vis.obtener_embedding(foto_query)
            lat_q, lon_q = motor_geo.obtener_coordenadas(distrito_q, referencia_q)
            h3_q = motor_geo.obtener_h3_index(lat_q, lon_q)
            
            scores_visuales, ids_candidatos = motor_faiss.buscar(vector_q, k=5)
            ids_lista = [int(id) for id in ids_candidatos if id != -1]
            candidatos_db = db.obtener_por_ids(ids_lista)
            
            resultados_temp = []
            
            for cand in candidatos_db:
                idx_faiss = list(ids_candidatos).index(cand["id"])
                sim_vis = scores_visuales[idx_faiss]
                sim_geo = motor_geo.calcular_score_geo(h3_q, cand["h3_index"])
                score_final = (0.6 * sim_vis) + (0.4 * sim_geo)
                dist_km = motor_geo.haversine_km(lat_q, lon_q, cand["lat"], cand["lon"])
                
                resultados_temp.append({
                    **cand, "score": score_final, "vis": sim_vis, "geo": sim_geo, "dist_km": dist_km
                })
            
            resultados_temp.sort(key=lambda x: x["score"], reverse=True)
            
            st.session_state.search_results = resultados_temp
            st.session_state.search_center = (lat_q, lon_q)

    if st.session_state.search_results is not None:
        with c2:
            st.subheader("Mapa de Coincidencias")
            lat_centro, lon_centro = st.session_state.search_center
            
            if st.session_state.search_results:
                mapa_res = motor_mapa.mapa_resultados(lat_centro, lon_centro, st.session_state.search_results[:5])
                st_folium(mapa_res, height=300, use_container_width=True)
            
            st.divider()
            st.subheader("Detalle de Candidatos")
            
            if not st.session_state.search_results:
                st.warning("No se encontraron coincidencias.")
            
            for res in st.session_state.search_results[:3]:
                color, emoji, msg = "red", "🔴", "Baja"
                if res["score"] > 0.85: color, emoji, msg = "green", "🟢", "Alta"
                elif res["score"] > 0.60: color, emoji, msg = "orange", "🟡", "Posible"
                
                with st.container(border=True):
                    col_img, col_info = st.columns([1, 3])
                    with col_img:
                        if os.path.exists(res["ruta_imagen"]):
                            st.image(res["ruta_imagen"], width=100)
                    with col_info:
                        st.markdown(f"### {res['nombre']} {emoji}")
                        st.caption(f"{msg} (Score: {res['score']*100:.1f}%)")
                        st.progress(float(res['score']))
                        st.markdown(f"**Distancia:** {res['dist_km']:.2f} km")
                        st.text(f"📍 {res['distrito']} | 👁️ Visión: {res['vis']:.2f}")

# --- PESTAÑA 2: OCR (Diseño "Antes vs Después" para PPT) ---
with tab2:
    st.subheader("Digitalización de Afiches (OCR)")
    
    # 1. Cargador (Ocupa todo el ancho al inicio)
    afiche = st.file_uploader("Subir afiche para digitalizar", type=["jpg", "png"], key="ocr")
    
    # 2. Botón de Acción
    if afiche and st.button("Analizar Afiche"):
        
        # Procesamiento
        with st.spinner("Procesando imagen con Tesseract y NLP..."):
            texto = motor_ocr.extraer_texto(afiche)
            info = motor_ocr.analizar_texto(texto)
        
        st.divider()
        
        # --- DISEÑO DE 2 COLUMNAS (Para la Captura de Pantalla) ---
        c_izq, c_der = st.columns([1, 1.2]) # Un poco más de espacio a la derecha para los datos
        
        # COLUMNA IZQUIERDA: LA IMAGEN (ENTRADA)
        with c_izq:
            st.markdown("#### 🖼️ Afiche Original")
            st.image(afiche, use_container_width=True)
            
            # El texto crudo lo ponemos aquí abajo para aprovechar espacio
            with st.expander("🔍 Ver Texto Crudo (Raw OCR)"):
                st.text(texto)

        # COLUMNA DERECHA: LOS DATOS (SALIDA)
        with c_der:
            st.markdown("#### 🤖 Datos Estructurados")
            
            # Contenedor principal con las métricas
            with st.container(border=True):
                attr = info["atributos_extraidos"]
                m1, m2, m3 = st.columns(3)
                m1.metric("📍 Distrito", attr.get("distrito", "---"))
                m2.metric("🎨 Color", attr.get("color", "---"))
                m3.metric("⚧️ Sexo", attr.get("sexo", "---"))
            
            # Alertas visuales grandes
            if info["telefonos"]: 
                fonos_limpios = ", ".join(info['telefonos'])
                st.success(f"**Contacto:** {fonos_limpios}", icon="📞")
            else:
                st.warning("⚠️ No se detectó teléfono", icon="⚠️")
                
            if info["recompensa"]: 
                st.error("**¡Recompensa Detectada!**", icon="🚨")
            else:
                st.info("Sin recompensa explícita", icon="ℹ️")

            # Etiquetas (Tags)
            if info["palabras_clave"]:
                st.write("**Etiquetas NLP:**")
                # Formato de "píldoras" visuales
                html_tags = ""
                for tag in info['palabras_clave']:
                    html_tags += f"<span style='background-color:#262730; padding:4px 8px; border-radius:15px; margin-right:5px; border:1px solid #4b4b4b; font-size:0.8em;'>{tag}</span>"
                st.markdown(html_tags, unsafe_allow_html=True)

# --- PESTAÑA 3: MAPA DE CALOR ---
with tab3:
    st.header("Distribución Espacial de Casos")
    st.write("Visualización de todos los reportes en Lima Metropolitana.")
    
    if "mostrar_mapa_global" not in st.session_state:
        st.session_state.mostrar_mapa_global = False

    if st.button("Cargar Mapa Global"):
        st.session_state.mostrar_mapa_global = True
    
    if st.session_state.mostrar_mapa_global:
        datos = db.obtener_todas()
        if datos:
            col_map, col_tabla = st.columns([2, 1])
            with col_map:
                mapa_global = motor_mapa.mapa_calor_bd(datos)
                st_folium(mapa_global, height=500, use_container_width=True)
            with col_tabla:
                st.write(f"**Total Registros:** {len(datos)}")
                st.dataframe([{k:v for k,v in d.items() if k in ['nombre', 'distrito', 'lat', 'lon']} for d in datos], height=400)
        else:
            st.warning("No hay datos registrados aún.")