# backend/services/vision_service.py
import os
from openai import OpenAI
from dotenv import load_dotenv
from backend.agents.prompts import VISION_DETAILED_PROMPT

load_dotenv()

class VisionService:
    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com/v1"
        )

    def analyze_financial_image(self, base64_image: str, text_query: str = None) -> str:
        """
        Analiza de forma aislada un extracto o comprobante financiero en Base64.
        """
        try:
            if not base64_image.startswith("data:image"):
                base64_image = f"data:image/jpeg;base64,{base64_image}"

            message_content = []
            if text_query:
                message_content.append({
                    "type": "text",
                    "text": f"Usuario pregunta: {text_query}"
                })

            message_content.extend([
                {"type": "text", "text": VISION_DETAILED_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": base64_image}
                }
            ])

            response = self.client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "user",
                        "content": message_content
                    }
                ],
                max_tokens=600
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error en VisionService: {str(e)}")
            return "Error al intentar analizar los datos visuales del documento."