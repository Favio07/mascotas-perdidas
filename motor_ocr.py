import pytesseract
from PIL import Image
import re

pytesseract.pytesseract.tesseract_cmd = r'D:\Tesseract-OCR\tesseract.exe'

class MotorOCR:
    def __init__(self):
        pass

    def extraer_texto(self, image_path_or_file):
        try:
            img = Image.open(image_path_or_file)
            texto = pytesseract.image_to_string(img)
            return texto
        except Exception as e:
            return f"Error OCR: {str(e)}"

    def analizar_texto(self, texto_crudo):
        datos = {
            "telefonos": [], "recompensa": False, 
            "palabras_clave": [], "atributos_extraidos": {}
        }
        
        if not texto_crudo: return datos
        texto_lower = texto_crudo.lower()

        # Teléfonos y Recompensa
        encontrados = re.findall(r'(?:9\d{2}[-\s]?\d{3}[-\s]?\d{3})', texto_crudo)
        for num in encontrados:
            limpio = num.replace(" ", "").replace("-", "")
            if len(limpio) == 9: datos["telefonos"].append(f"+51{limpio}")

        if re.search(r'(recompensa|s/|soles|\$)', texto_lower): datos["recompensa"] = True

        # Palabras clave y Atributos básicos
        keywords = ["blanco", "negro", "marrón", "café", "crema", "caramelo", "dorado", "gris", "manchas", 
                    "chico", "pequeño", "mediano", "grande", "macho", "hembra", "perro", "gato"]
        datos["palabras_clave"] = [w for w in keywords if w in texto_lower]

        # Búsqueda Estricta (Color: X)
        patrones = {
            "color": r'color\s*[:\.]?\s*([a-zA-Z\s]+)',
            "raza": r'raza\s*[:\.]?\s*([a-zA-Z\s]+)',
            "sexo": r'sexo\s*[:\.]?\s*([a-zA-Z\s]+)'
        }
        for k, v in patrones.items():
            m = re.search(v, texto_lower)
            if m: datos["atributos_extraidos"][k] = m.group(1).split('\n')[0].title()

        # Fallbacks
        if "color" not in datos["atributos_extraidos"]:
            for c in ["blanco", "negro", "marrón", "caramelo", "crema", "dorado"]:
                if c in texto_lower: 
                    datos["atributos_extraidos"]["color"] = c.title(); break
        
        if "sexo" not in datos["atributos_extraidos"]:
            if "macho" in texto_lower: datos["atributos_extraidos"]["sexo"] = "Macho"
            elif "hembra" in texto_lower: datos["atributos_extraidos"]["sexo"] = "Hembra"

        # --- FALLBACK DISTRITOS (Tus 43 exactos) ---
        # Ordenados por longitud para que encuentre "San Juan de Lurigancho" antes que "San Juan"
        distritos_target = [
            "villa maría del triunfo", "san juan de lurigancho", "san juan de miraflores", 
            "santiago de surco", "san martín de porres", "santa maría del mar", "magdalena del mar", 
            "villa el salvador", "carmen de la legua", "lurigancho", "la victoria", "puente piedra", 
            "punta hermosa", "independencia", "el agustino", "jesús maría", "pueblo libre", 
            "pachacamac", "san bartolo", "san isidro", "san miguel", "santa anita", "santa rosa", 
            "carabayllo", "chaclacayo", "chorrillos", "cieneguilla", "la molina", "los olivos", 
            "miraflores", "punta negra", "san borja", "san luis", "surquillo", "barranco", 
            "pucusana", "san luis", "ancon", "breña", "comas", "lince", "lurin", "rimac", "lima", "ate"
        ]

        for d in distritos_target:
            if d in texto_lower:
                # Aquí hacemos el match con la lista bonita de app.py
                # Mapeo manual rápido para corregir tildes al mostrar
                nombre_final = d.title()
                if d == "ancon": nombre_final = "Ancon"
                if d == "ate": nombre_final = "Ate"
                # (El sistema usará el string detectado, que es suficiente para el MVP)
                datos["atributos_extraidos"]["distrito"] = nombre_final
                break

        return datos