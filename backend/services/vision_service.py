import os
import httpx
from openai import OpenAI
from dotenv import load_dotenv
from backend.agents.prompts import VISION_DETAILED_PROMPT

load_dotenv()

class VisionService:
    def __init__(self):
        # 1. Creamos un transporte que ignora explícitamente cualquier proxy del sistema
        transport = httpx.HTTPTransport(proxy=None)
        custom_http_client = httpx.Client(transport=transport)
        
        # 2. Inyectamos el cliente limpio para evitar el error de 'proxies'
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=custom_http_client
        )

    def analyze_diagram(self, base64_image: str, text_query: str = None) -> str:
        """
        Analiza diagramas eléctricos y esquemáticos técnicos usando GPT-4o.
        """
        try:
            if not base64_image.startswith("data:image"):
                base64_image = f"data:image/jpeg;base64,{base64_image}"

            message_content = []
            if text_query:
                message_content.append({
                    "type": "text", 
                    "text": f"Contexto del usuario: {text_query}"
                })

            message_content.extend([
                {"type": "text", "text": f"Actúa como un experto en Ingeniería Eléctrica. {VISION_DETAILED_PROMPT}"},
                {
                    "type": "image_url",
                    "image_url": {"url": base64_image}
                }
            ])

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Eres AmpereVision, experto en interpretar diagramas eléctricos, planos y componentes de circuitos."},
                    {"role": "user", "content": message_content}
                ],
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error en VisionService: {str(e)}")
            return "Lo siento, no pude procesar el diagrama eléctrico."