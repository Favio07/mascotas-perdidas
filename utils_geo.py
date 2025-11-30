import h3
import math
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

class MotorGeo:
    def __init__(self, resolucion=9):
        self.resolucion = resolucion
        # Inicializamos el geocodificador con un nombre de usuario único para tu tesis
        self.geolocator = Nominatim(user_agent="tesis_mascotas_upc_v1")
        
        # Coordenadas aproximadas (Backup por si falla el geocoding)
        self.coordenadas_distritos = {
            "Ancon": (-11.7731, -77.1468), "Ate": (-12.0256, -76.9186), "Barranco": (-12.1496, -77.0217),
            "Breña": (-12.0569, -77.0536), "Carabayllo": (-11.8976, -77.0256), "Chaclacayo": (-11.9731, -76.7742),
            "Chorrillos": (-12.1767, -77.0161), "Cieneguilla": (-12.1136, -76.7739), "Comas": (-11.9372, -77.0546),
            "El Agustino": (-12.0428, -76.9969), "Independencia": (-11.9933, -77.0547), "Jesús María": (-12.0769, -77.0467),
            "La Molina": (-12.0778, -76.9256), "La Victoria": (-12.0644, -77.0169), "Lima": (-12.0464, -77.0428),
            "Lince": (-12.0842, -77.0342), "Los Olivos": (-11.9667, -77.0739), "Lurigancho": (-11.9347, -76.6975),
            "Lurín": (-12.2728, -76.8708), "Magdalena del Mar": (-12.0914, -77.0669), "Miraflores": (-12.1111, -77.0316),
            "Pachacamac": (-12.2286, -76.8633), "Pucusana": (-12.4794, -76.7972), "Pueblo Libre": (-12.0764, -77.0617),
            "Puente Piedra": (-11.8664, -77.0753), "Punta Hermosa": (-12.3347, -76.8247), "Punta Negra": (-12.3656, -76.7950),
            "Rimac": (-12.0336, -77.0269), "San Bartolo": (-12.3886, -76.7814), "San Borja": (-12.1075, -77.0028),
            "San Isidro": (-12.0975, -77.0364), "San Juan de Lurigancho": (-11.9767, -77.0036), "San Juan de Miraflores": (-12.1622, -76.9686),
            "San Luis": (-12.0764, -76.9947), "San Martín de Porres": (-11.9919, -77.0825), "San Miguel": (-12.0786, -77.0856),
            "Santa Anita": (-12.0436, -76.9594), "Santa María del Mar": (-12.4042, -76.7744), "Santa Rosa": (-11.8036, -77.1625),
            "Santiago de Surco": (-12.1419, -76.9922), "Surquillo": (-12.1128, -77.0122), "Villa El Salvador": (-12.2169, -76.9414),
            "Villa María del Triunfo": (-12.1594, -76.9297)
        }

    def obtener_h3_index(self, lat, lon):
        try:
            return h3.latlng_to_cell(lat, lon, self.resolucion)
        except:
            return None

    def haversine_km(self, lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat / 2) * math.sin(dlat / 2) + \
            math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
            math.sin(dlon / 2) * math.sin(dlon / 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def calcular_score_geo(self, h3_origen, h3_destino):
        try:
            if h3_origen == h3_destino: return 1.0
            lat1, lon1 = h3.cell_to_latlng(h3_origen)
            lat2, lon2 = h3.cell_to_latlng(h3_destino)
            distancia_km = self.haversine_km(lat1, lon1, lat2, lon2)
            
            max_radio_km = 20.0 
            if distancia_km > max_radio_km: return 0.0
            
            score = 1 - (distancia_km / max_radio_km)
            return max(0.0, score)
        except:
            return 0.0

    def obtener_coordenadas(self, distrito, referencia=""):
        """
        Intenta obtener coordenadas exactas de una referencia.
        Si no hay referencia o falla, devuelve el centro del distrito.
        """
        lat_default, lon_default = self.coordenadas_distritos.get(distrito, (-12.0464, -77.0428))
        
        if not referencia:
            return lat_default, lon_default
            
        try:
            # Construimos la búsqueda: "Parque Kennedy, Miraflores, Lima, Peru"
            query = f"{referencia}, {distrito}, Lima, Peru"
            location = self.geolocator.geocode(query, timeout=5)
            
            if location:
                return location.latitude, location.longitude
            else:
                # Si no encuentra la calle exacta, devolvemos el distrito
                return lat_default, lon_default
        except Exception as e:
            print(f"Error Geocoding: {e}")
            return lat_default, lon_default