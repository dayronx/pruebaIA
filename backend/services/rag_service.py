# backend/services/rag_service.py
import os
import json
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import numpy as np

class RAGService:
    def __init__(self, storage_path="backend/database/rag_store.json"):
        self.storage_path = storage_path
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.documents = []
        self.vectors = []
        self.load_vector_store()

    def scrape_and_index(self, url: str):
        """Descarga una URL, extrae el texto limpio y lo indexa para RAG (Reto 04)."""
        try:
            headers = {"User-Agent": "Mozilla/5.0 FinBotScraper/1.0"}
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                return {"status": "error", "message": f"HTTP Error {response.status_code}"}

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Limpiar etiquetas innecesarias
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.extract()
                
            text = soup.get_text(separator=" ")
            # Limpieza básica de espacios en blanco
            lines = (line.strip() for line in text.splitlines())
            chunks = [phrase.strip() for line in lines for phrase in line.split("  ") if len(phrase.strip()) > 40]
            
            # Tomar los bloques de texto más relevantes (primeros 15 chunks para el simulacro)
            selected_chunks = chunks[:15]
            
            if not selected_chunks:
                return {"status": "error", "message": "No se extrajo contenido textual relevante de la URL."}

            print(f"Generando embeddings para {len(selected_chunks)} fragmentos extraídos de: {url}")
            res = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=selected_chunks
            )
            
            # Formatear la data estructurada
            for i, item in enumerate(res.data):
                self.documents.append({"url": url, "text": selected_chunks[i]})
                self.vectors.append(item.embedding)

            # Persistir la base de conocimientos vectorial local
            self.save_vector_store()
            return {"status": "success", "chunks_indexed": len(selected_chunks)}

        except Exception as e:
            return {"status": "error", "message": f"Fallo en proceso RAG/Scraping: {str(e)}"}

    def query_knowledge(self, query: str, limit: int = 2) -> str:
        """Busca en caliente los fragmentos de páginas web indexadas que asistan al usuario."""
        if not self.vectors:
            return ""

        try:
            res = self.client.embeddings.create(model="text-embedding-3-small", input=[query])
            query_vector = np.array(res.data[0].embedding)
            
            scores = []
            for vec in self.vectors:
                syn = np.dot(query_vector, np.array(vec)) / (np.linalg.norm(query_vector) * np.linalg.norm(vec))
                scores.append(syn)
                
            top_indices = np.argsort(scores)[::-1][:limit]
            
            context_blocks = []
            for idx in top_indices:
                if scores[idx] > 0.35:  # Umbral laxo para RAG informativo
                    context_blocks.append(f"[Fuente: {self.documents[idx]['url']}]: {self.documents[idx]['text']}")
                    
            return "\n\n".join(context_blocks)
        except Exception as e:
            print(f"Error consultando RAG local: {str(e)}")
            return ""

    def save_vector_store(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump({"documents": self.documents, "vectors": self.vectors}, f, ensure_ascii=False)

    def load_vector_store(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", [])
                    self.vectors = data.get("vectors", [])
            except Exception:
                pass