import os
import json
import numpy as np
import httpx
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class SemanticCacheService:
    def __init__(self, db_path="backend/database/cache_db.json"):
        self.db_path = db_path
        
        # Configuración del cliente para evitar el error de 'proxies'
        transport = httpx.HTTPTransport(proxy=None)
        custom_http_client = httpx.Client(transport=transport)
        
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=custom_http_client
        )
        
        self.cache_data = []
        self.vectors = []
        self.load_cache()

    def load_cache(self):
        """Carga y procesa el caché desde el archivo JSON."""
        if not os.path.exists(self.db_path):
            print(f"Archivo de caché no encontrado: {self.db_path}")
            return
            
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.cache_data = json.load(f)
            
            if not self.cache_data:
                return

            questions = [item.get("pregunta", "") for item in self.cache_data]
            
            # Generar embeddings
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=questions
            )
            
            self.vectors = [data.embedding for data in response.data]
            print("Caché cargado correctamente.")
            
        except Exception as e:
            print(f"Error al cargar caché: {str(e)}")