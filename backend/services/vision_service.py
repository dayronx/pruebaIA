# backend/services/vision_service.py
import os
from openai import OpenAI
from dotenv import load_dotenv
from backend.agents.prompts import VISION_DETAILED_PROMPT

load_dotenv()

class VisionService:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def analyze_financial_image(self, base64_image: str) -> str:
        """
        Analiza de forma aislada un extracto o comprobante financiero en Base64.
        """
        try:
            if not base64_image.startswith("data:image"):
                base64_image = f"data:image/jpeg;base64,{base64_image}"

            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": VISION_DETAILED_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": base64_image}
                            }
                        ]
                    }
                ],
                max_tokens=600
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error en VisionService: {str(e)}")
            return "Error al intentar analizar los datos visuales del documento."