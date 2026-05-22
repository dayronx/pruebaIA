import base64
import os
import time
import uuid
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Importaciones de tus servicios
from backend.services.cache_service import SemanticCacheService
from backend.services.voice_service import VoiceService
from backend.services.scraper_service import ScraperService
from backend.services.vision_service import VisionService 
from backend.agents.ampere_agent import AmpereBotAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="AmpereBot Backend Core", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Servicios
cache_service = SemanticCacheService()
voice_service = VoiceService()
scraper_service = ScraperService()
vision_service = VisionService()
bot_agent = AmpereBotAgent()

# CONFIGURACIÓN DE RUTA ABSOLUTA PARA EVITAR ERRORES 404
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(BASE_DIR, "tmp")
os.makedirs(TMP_DIR, exist_ok=True)

# Montar carpeta estática
app.mount("/tmp", StaticFiles(directory=TMP_DIR), name="tmp")

class ChatRequest(BaseModel):
    session_id: str
    message: Optional[str] = None
    image_base64: Optional[str] = None
    audio_base64: Optional[str] = None
    input_mode: Optional[str] = None
    output_mode: Optional[str] = "text"

def _save_base64_to_temp(base64_data: str, prefix: str) -> str:
    extension = ".webm" 
    if "," in base64_data:
        header, base64_data = base64_data.split(",", 1)
        header = header.lower()
        if "mpeg" in header or "mp3" in header: extension = ".mp3"
        elif "ogg" in header or "opus" in header: extension = ".ogg"
        elif "mp4" in header or "m4a" in header: extension = ".mp4"
        elif "wav" in header: extension = ".wav"
        elif "webm" in header: extension = ".webm"
    temp_path = os.path.join(TMP_DIR, f"{prefix}_{uuid.uuid4()}{extension}")
    with open(temp_path, "wb") as out_file:
        out_file.write(base64.b64decode(base64_data))
    return temp_path

@app.post("/api/chat")
async def handle_chat_request(chat_request: ChatRequest):
    try:
        start_time = time.time()
        textInput = chat_request.message
        imageInput = chat_request.image_base64
        output_mode = (chat_request.output_mode or "text").lower()

        # 1. Transcripción de Audio
        if chat_request.audio_base64:
            temp_audio = _save_base64_to_temp(chat_request.audio_base64, "in")
            textInput = voice_service.transcribe_audio(temp_audio)
            os.remove(temp_audio)
            
            if not textInput or textInput.strip() == "":
                return {
                    "response": "No pude entender el audio o el formato no es compatible. Por favor, intenta de nuevo.",
                    "audioUrl": None,
                    "latencySeconds": round(time.time() - start_time, 2)
                }

        # 2. Lógica del Agente
        if imageInput:
            base64_puro = imageInput.split(",", 1)[1] if "," in imageInput else imageInput
            response_text = vision_service.analyze_diagram(base64_puro, textInput)
        else:
            rag_context = scraper_service.search_chunks(textInput) if textInput else ""
            context = f"{textInput}\n\nContexto Técnico:\n{rag_context}" if rag_context else textInput
            result = bot_agent.run(session_id=chat_request.session_id, text_input=context)
            response_text = result.get("response", "Error procesando.")

        # 3. Generación de Voz (TTS)
        audio_url = None
        if output_mode == 'audio':
            out_filename = f"out_{uuid.uuid4()}.mp3"
            out_path = os.path.join(TMP_DIR, out_filename)
            if voice_service.text_to_speech(response_text, out_path):
                # La URL devuelta es relativa al servidor, StaticFiles la resolverá
                audio_url = f"/tmp/{out_filename}"

        return {
            "response": response_text,
            "audioUrl": audio_url,
            "latencySeconds": round(time.time() - start_time, 2)
        }

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))