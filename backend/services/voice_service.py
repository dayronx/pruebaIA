# backend/services/voice_service.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

class VoiceService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def transcribe_audio(self, file_path: str) -> str:
        """Transcribe un archivo de audio (mp3/wav/m4a) a texto usando Whisper."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Archivo de audio no encontrado en: {file_path}")
            
        try:
            with open(file_path, "rb") as audio_file:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            return transcript.text
        except Exception as e:
            print(f"Error en STT Whisper: {str(e)}")
            return ""

    def text_to_speech(self, text: str, output_path: str) -> bool:
        """Convierte texto en un archivo MP3 utilizando OpenAI TTS."""
        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",  # Voz profesional y neutral
                input=text
            )
            # Guardar el flujo de audio directamente en el disco duro
            response.stream_to_file(output_path)
            return True
        except Exception as e:
            print(f"Error en TTS OpenAI: {str(e)}")
            return False