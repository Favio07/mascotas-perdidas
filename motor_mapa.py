import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import h3 # <--- IMPORTANTE: Necesitamos H3 aquí para la privacidad

class MotorMapa:
    def __init__(self):
        pass

    def mapa_resultados(self, lat_centro, lon_centro, resultados):
        """
        TAB 1: Círculos de Privacidad (Búsqueda).
        """
        lat_c = float(lat_centro)
        lon_c = float(lon_centro)
        
        m = folium.Map(location=[lat_c, lon_c], zoom_start=14)

        folium.Marker(
            [lat_c, lon_c],
            tooltip="Tu ubicación",
            icon=folium.Icon(color="blue", icon="user", prefix="fa")
        ).add_to(m)

        for res in resultados:
            try:
                r_lat = float(res["lat"])
                r_lon = float(res["lon"])
                
                # APLICAMOS PRIVACIDAD TAMBIÉN AQUÍ
                # Movemos el centro del círculo al centro del Hexágono H3
                # Resolución 9 = Hexágonos de ~170 metros de lado
                h3_idx = h3.latlng_to_cell(r_lat, r_lon, 9)
                r_lat, r_lon = h3.cell_to_latlng(h3_idx)

                color = "#d32f2f"
                if res["score"] > 0.85: color = "#388e3c"
                elif res["score"] > 0.60: color = "#f57c00"

                html = f"<b>{res['nombre']}</b><br>Match: {res['score']*100:.0f}%"
                
                folium.Circle(
                    location=[r_lat, r_lon],
                    radius=300, # Radio visual grande
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.3,
                    popup=html,
                    tooltip="Zona H3 (Anonimizada)"
                ).add_to(m)
            except ValueError:
                continue 

        return m

    def mapa_calor_bd(self, todos_registros):
        """
        TAB 3: Mapa de Calor con GRID SNAPPING (Privacidad Real).
        """
        m = folium.Map(location=[-12.0464, -77.0428], zoom_start=11)

        heat_data = []
        
        for p in todos_registros:
            try:
                lat = float(p["lat"])
                lon = float(p["lon"])
                
                if lat != 0 and lon != 0:
                    # --- TÉCNICA DE PRIVACIDAD: GRID SNAPPING ---
                    # 1. Convertimos la coordenada exacta a un índice H3 (Hexágono)
                    # Resolución 9 es aprox el tamaño de una manzana/cuadra grande.
                    h3_index = h3.latlng_to_cell(lat, lon, 9)
                    
                    # 2. Obtenemos el CENTRO de ese hexágono
                    lat_c, lon_c = h3.cell_to_latlng(h3_index)
                    
                    # 3. Graficamos el CENTRO, no la casa real.
                    # Así, todos los puntos de la zona se apilan en el mismo lugar.
                    heat_data.append([lat_c, lon_c, 1.0])
                    
            except (ValueError, TypeError):
                continue

        if heat_data:
            # Aumentamos el radio y el blur para que se vea más como una "nube"
            HeatMap(
                heat_data,
                radius=25,  # Radio más grande (píxeles)
                blur=20,    # Más difuminado
                min_opacity=0.4,
                gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}
            ).add_to(m)
            
        return m