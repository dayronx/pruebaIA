# backend/services/cache_service.py
import os
import json
import numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Constante de configuración requerida por el reto (Fácilmente modificable)
SIMILARITY_THRESHOLD = 0.90

class SemanticCacheService:
    def __init__(self, db_path="backend/database/cache_db.json"):
        self.db_path = db_path
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.cache_data = []
        self.vectors = []
        self.load_cache()

    def load_cache(self):
        """Carga las preguntas del archivo JSON y pre-calcula sus embeddings."""
        if not os.path.exists(self.db_path):
            return
            
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.cache_data = json.load(f)
            
            if not self.cache_data:
                return

            print(f"Indexando {len(self.cache_data)} elementos en el caché semántico de FinBot...")
            
            # Extraer solo los textos de las preguntas para vectorizar en lote
            questions = [item["pregunta"] for item in self.cache_data]
            
            # Llamada masiva a la API de OpenAI para ahorrar latencia en el inicio
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=questions
            )
            
            # Almacenar los vectores generados en una lista mapeada
            self.vectors = [data.embedding for data in response.data]
            print("¡Indexación del caché semántico completada con éxito!")
            
        except Exception as e:
            print(f"Error al inicializar caché semántico: {str(e)}")

    def _cosine_similarity(self, vec_a, vec_b):
        """Calcula la similitud coseno matemática exacta entre dos vectores."""
        a = np.array(vec_a)
        b = np.array(vec_b)
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def search_cache(self, user_query: str):
        """
        Busca si la consulta del usuario tiene un hit semántico en nuestra base de conocimientos.
        Retorna la respuesta si supera el umbral, de lo contrario retorna None.
        """
        if not self.vectors:
            return None

        try:
            # 1. Generar embedding de la pregunta entrante
            query_response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=[user_query]
            )
            query_vector = query_response.data[0].embedding

            # 2. Iterar sobre todos los vectores pre-calculados y buscar la mayor similitud
            best_score = -1
            best_match_index = -1

            for i, cache_vector in enumerate(self.vectors):
                similarity = self._cosine_similarity(query_vector, cache_vector)
                if similarity > best_score:
                    best_score = similarity
                    best_match_index = i

            # 3. Validar contra el umbral configurable
            if best_score >= SIMILARITY_THRESHOLD:
                print(f"[HIT CACHÉ] Similitud: {best_score:.4f} -> {self.cache_data[best_match_index]['pregunta']}")
                return {
                    "source": "cache",
                    "response": self.cache_data[best_match_index]["respuesta"],
                    "score": best_score
                }
            
            print(f"[MISS CACHÉ] Mayor similitud encontrada fue: {best_score:.4f}. Pasando al LLM.")
            return None

        except Exception as e:
            print(f"Error en la búsqueda del caché semántico: {str(e)}")
            return None

    def add_to_cache(self, pregunta: str, respuesta: str):
        """Guarda dinámicamente nuevas interacciones resueltas por el LLM en el caché."""
        try:
            query_response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=[pregunta]
            )
            new_vector = query_response.data[0].embedding
            
            # Añadir a las estructuras en caliente
            new_item = {"pregunta": pregunta, "respuesta": respuesta}
            self.cache_data.append(new_item)
            self.vectors.append(new_vector)
            
            # Persistir en el disco duro local
            with open(self.db_path, "w", encoding="utf-8") as f:
                json.dump(self.cache_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"No se pudo guardar la nueva entrada en el caché dinámico: {str(e)}")