# backend/main.py
import base64
import os
import time
import uuid
import shutil
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Importar todos nuestros servicios core
from backend.services.cache_service import SemanticCacheService
from backend.services.voice_service import VoiceService
from backend.services.rag_service import RAGService
from backend.agents.finbot_agent import FinBotAgent

app = FastAPI(title="FinBot Backend Core", version="2.0")

# Habilitar CORS para integración transparente con React/Vite (Reto 08)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar en producción por el dominio del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar servicios en memoria única
cache_service = SemanticCacheService()
voice_service = VoiceService()
rag_service = RAGService()
bot_agent = FinBotAgent()

# Directorio temporal para manejar audios entrantes y salientes
TMP_DIR = "backend/tmp"
os.makedirs(TMP_DIR, exist_ok=True)

class ChatRequest(BaseModel):
    session_id: str
    message: Optional[str] = None
    image_base64: Optional[str] = None
    audio_base64: Optional[str] = None
    input_mode: Optional[str] = None
    output_mode: Optional[str] = None


def _save_base64_to_temp(base64_data: str, prefix: str, suffix: str = ".bin") -> str:
    extension = suffix
    if "," in base64_data:
        header, base64_data = base64_data.split(",", 1)
        if "audio/webm" in header:
            extension = ".webm"
        elif "audio/ogg" in header:
            extension = ".ogg"
        elif "audio/mpeg" in header or "audio/mp3" in header:
            extension = ".mp3"
        elif "audio/wav" in header:
            extension = ".wav"
        elif "image/png" in header:
            extension = ".png"
        elif "image/jpeg" in header or "image/jpg" in header:
            extension = ".jpg"
        elif "image/webp" in header:
            extension = ".webp"
    temp_path = os.path.join(TMP_DIR, f"{prefix}_{uuid.uuid4()}{extension}")
    with open(temp_path, "wb") as out_file:
        out_file.write(base64.b64decode(base64_data))
    return temp_path


@app.post("/api/chat")
async def handle_chat_request(chat_request: ChatRequest):
    """
    Controlador único unificado de la API de FinBot.
    Procesa texto, voz, caché y lógica conversacional del agente.
    """
    start_time = time.time()
    voice_triggered = False
    session_id = chat_request.session_id
    textInput = chat_request.message or None
    imageInput = chat_request.image_base64 or None
    audio_base64 = chat_request.audio_base64 or None
    temp_audio_in = None

    output_mode = (chat_request.output_mode or "text").lower()

    if audio_base64:
        voice_triggered = True
        temp_audio_in = _save_base64_to_temp(audio_base64, "in")
        textInput = voice_service.transcribe_audio(temp_audio_in)
        if temp_audio_in and os.path.exists(temp_audio_in):
            os.remove(temp_audio_in)

    if not textInput and not imageInput:
        raise HTTPException(status_code=400, detail="Debe proporcionar una consulta en texto, voz o imagen.")

    # 2. Pipeline de consulta al Caché Semántico (Reto 06) - Ignorado si hay imagen adjunta
    if textInput and not imageInput:
        cache_hit = cache_service.search_cache(textInput)
        if cache_hit:
            latency = time.time() - start_time
            
            # Si el usuario pidió audio de salida o viene por voz, generar TTS
            audio_url = None
            if output_mode == 'audio' or voice_triggered:
                out_filename = f"out_{uuid.uuid4()}.mp3"
                temp_audio_out = os.path.join(TMP_DIR, out_filename)
                if voice_service.text_to_speech(cache_hit["response"], temp_audio_out):
                    audio_url = f"/api/voice/download/{out_filename}"

            return {
                "source": "cache",
                "sourceName": "Semantic Cache (90% Similarity)",
                "response": cache_hit["response"],
                "audioUrl": audio_url,
                "latencySeconds": round(latency, 2)
            }

    # 3. Pipeline RAG (Inyectar contexto web de fondo si aplica)
    rag_context = ""
    if textInput:
        rag_context = rag_service.query_knowledge(textInput)
        if rag_context:
            textInput = f"{textInput}\n\n[CONTEXTO WEB ADICIONAL PARA TU ANÁLISIS]:\n{rag_context}"

    # 4. Procesar con el Agente Multi-herramientas / Multimodal
    agent_result = bot_agent.run(session_id=session_id, text_input=textInput, base64_image=imageInput)

    # Si la interacción fue exitosa y directa del LLM, guardarla en el caché dinámico para el futuro
    if agent_result["source"] == "llm" and textInput and not imageInput and not rag_context:
        cache_service.add_to_cache(textInput, agent_result["response"])

    # 5. Pipeline de Salida de Voz (Reto 03)
    audio_url = None
    if agent_result["response"] and (voice_triggered or output_mode == 'audio'):
        out_filename = f"out_{uuid.uuid4()}.mp3"
        temp_audio_out = os.path.join(TMP_DIR, out_filename)
        if voice_service.text_to_speech(agent_result["response"], temp_audio_out):
            audio_url = f"/api/voice/download/{out_filename}"

    latency = time.time() - start_time

    return {
        "source": agent_result["source"],
        "sourceName": agent_result["sourceName"],
        "response": agent_result["response"],
        "audioUrl": audio_url,
        "latencySeconds": round(latency, 2)
    }

@app.post("/api/rag/index")
async def index_url(payload: dict):
    """Endpoint administrativo para inyectar URLs a la base de conocimiento (Reto 04)."""
    target_url = payload.get("url")
    if not target_url:
        raise HTTPException(status_code=400, detail="Se requiere el campo 'url' en el JSON.")
        
    result = rag_service.scrape_and_index(target_url)
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])
    return result

@app.get("/api/voice/download/{filename}")
async def download_audio(filename: str):
    """Devuelve los archivos MP3 generados por el sintetizador al cliente web."""
    file_path = os.path.join(TMP_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo de audio no encontrado.")
    return FileResponse(file_path, media_type="audio/mpeg")