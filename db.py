import sqlite3
import numpy as np

DB_NAME = "tesis_mascotas.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS mascotas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            distrito TEXT,
            h3_index TEXT,
            lat REAL,
            lon REAL,
            ruta_imagen TEXT,
            embedding BLOB,
            fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def guardar_mascota(nombre, distrito, h3_index, lat, lon, ruta_img, embedding_array):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    embedding_blob = embedding_array.tobytes()
    
    c.execute('''
        INSERT INTO mascotas (nombre, distrito, h3_index, lat, lon, ruta_imagen, embedding)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (nombre, distrito, h3_index, lat, lon, ruta_img, embedding_blob))
    
    id_generado = c.lastrowid
    conn.commit()
    conn.close()
    return id_generado

def obtener_todas():
    """
    CORREGIDO: Ahora incluye lat y lon en el SELECT
    """
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Agregamos lat, lon a la consulta
    c.execute("SELECT id, nombre, distrito, h3_index, ruta_imagen, embedding, lat, lon FROM mascotas")
    filas = c.fetchall()
    conn.close()
    
    resultados = []
    for fila in filas:
        emb_array = np.frombuffer(fila[5], dtype=np.float32)
        resultados.append({
            "id": fila[0],
            "nombre": fila[1],
            "distrito": fila[2],
            "h3_index": fila[3],
            "ruta_imagen": fila[4],
            "vector": emb_array,
            "lat": fila[6], # <--- AHORA SÍ EXISTE
            "lon": fila[7]  # <--- AHORA SÍ EXISTE
        })
    return resultados

def obtener_por_ids(lista_ids):
    """
    CORREGIDO: También incluye lat y lon
    """
    if not len(lista_ids): return []
    
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    
    query = f"SELECT id, nombre, distrito, h3_index, ruta_imagen, embedding, lat, lon FROM mascotas WHERE id IN ({','.join(map(str, lista_ids))})"
    c.execute(query)
    filas = c.fetchall()
    conn.close()
    
    resultados = []
    for fila in filas:
        emb_array = np.frombuffer(fila[5], dtype=np.float32)
        resultados.append({
            "id": fila[0],
            "nombre": fila[1],
            "distrito": fila[2],
            "h3_index": fila[3],
            "ruta_imagen": fila[4],
            "vector": emb_array,
            "lat": fila[6], # <--- IMPORTANTE
            "lon": fila[7]  # <--- IMPORTANTE
        })
    return resultados