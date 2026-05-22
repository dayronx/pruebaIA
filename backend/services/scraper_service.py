import os
import json
import requests
from bs4 import BeautifulSoup

class ScraperService:
    def __init__(self, storage_path="backend/database/scraper_store.json"):
        # Asegura que el directorio exista
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        self.storage_path = storage_path
        self.chunks = []
        self.load_store()

    def scrape_and_index(self, url: str):
        """Descarga y limpia contenido técnico de All About Circuits."""
        try:
            headers = {"User-Agent": "AmpereBot/1.0 (Educational Project)"}
            response = requests.get(url, headers=headers, timeout=15)
            
            if response.status_code != 200:
                return {"status": "error", "message": f"HTTP Error {response.status_code}"}

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remover ruido
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()
                
            text = soup.get_text(separator=" ")
            
            # Chunking técnico: dividir por párrafos largos y filtrar ruido
            paragraphs = [p.strip() for p in text.split('\n') if len(p.strip()) > 50]
            self.chunks = [{"url": url, "text": p} for p in paragraphs[:40]]
            
            self.save_store()
            return {"status": "success", "chunks_indexed": len(self.chunks)}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def search_chunks(self, query: str, limit: int = 3) -> str:
        """Busca fragmentos relevantes basados en la consulta del usuario."""
        if not self.chunks:
            return "No hay información técnica indexada."
        
        results = [c["text"] for c in self.chunks if any(word.lower() in c["text"].lower() for word in query.split())]
        
        if not results:
            return "No se encontraron detalles específicos sobre ese tema eléctrico."
            
        return "\n\n".join(results[:limit])

    def save_store(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump({"chunks": self.chunks}, f, ensure_ascii=False)

    def load_store(self):
        if os.path.exists(self.storage_path):
            with open(self.storage_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.chunks = data.get("chunks", [])