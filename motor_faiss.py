import faiss
import numpy as np
import pickle
import os

class MotorFAISS:
    def __init__(self, dimension=512):
        self.dimension = dimension
        # Usamos IndexFlatIP (Inner Product). 
        # Si los vectores están normalizados, esto equivale a Similitud Coseno.
        self.index = faiss.IndexIDMap(faiss.IndexFlatIP(dimension))

    def agregar_vector(self, id_db, vector):
        """
        Agrega un vector al índice asociado a un ID de la base de datos.
        El vector debe ser float32 y estar normalizado.
        """
        vector = np.array([vector], dtype=np.float32)
        faiss.normalize_L2(vector) # Normalizar para que IP = Coseno
        
        # FAISS requiere IDs en formato int64
        id_array = np.array([id_db], dtype=np.int64)
        self.index.add_with_ids(vector, id_array)

    def buscar(self, vector_query, k=5):
        """
        Busca los k vectores más similares.
        Retorna: (distancias, ids)
        """
        vector_query = np.array([vector_query], dtype=np.float32)
        faiss.normalize_L2(vector_query)
        
        # Buscamos en el índice
        D, I = self.index.search(vector_query, k)
        
        # D son las distancias (scores de similitud)
        # I son los IDs de la base de datos
        return D[0], I[0]

    def cantidad(self):
        return self.index.ntotal

    def limpiar(self):
        self.index.reset()