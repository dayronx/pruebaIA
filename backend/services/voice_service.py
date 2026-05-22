import os
import httpx
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class VoiceService:
    def __init__(self):
        # CORRECCIÓN: Configuramos el cliente para ignorar la verificación SSL
        # Esto permite que el firewall de RIWI no corte la conexión al interceptar el tráfico
        custom_http_client = httpx.Client(
            verify=False, # Vital para evitar el error 421 en redes bloqueadas
            timeout=30.0
        )
        
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=custom_http_client
        )

    def transcribe_audio(self, file_path: str) -> str:
        if not os.path.exists(file_path):
            print(f"Error: Archivo no encontrado en {file_path}")
            return ""
            
        try:
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            return transcript.text
        except Exception as e:
            print(f"ERROR DETALLADO Whisper: {str(e)}")
            return ""

    def text_to_speech(self, text: str, output_path: str) -> bool:
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text
            )
            response.stream_to_file(output_path)
            return True
        except Exception as e:
            print(f"ERROR DETALLADO TTS: {str(e)}")
            return False