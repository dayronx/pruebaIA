# backend/agents/finbot_agent.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# CORRECCIÓN: Importar el prompt centralizado desde el módulo de agentes
from backend.agents.prompts import SYSTEM_PROMPT
from backend.tools.financial_tools import calculate_interest, get_usd_rate
from backend.tools.external_api import get_crypto_price

load_dotenv()

class FinBotAgent:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.sessions_memory = {}

    def _get_or_create_memory(self, session_id: str) -> list:
        """Mantiene el historial de chat de la sesión."""
        if session_id not in self.sessions_memory:
            self.sessions_memory[session_id] = []
        return self.sessions_memory[session_id]

    def _enforce_memory_limit(self, session_id: str):
        """Asegura que solo se recuerden las últimas 7 interacciones completas (User + Assistant)."""
        # 7 interacciones completas = 14 entradas en la lista
        if len(self.sessions_memory[session_id]) > 14:
            self.sessions_memory[session_id] = self.sessions_memory[session_id][-14:]

    def _get_tools_definition(self) -> list:
        """Define el esquema JSON de las herramientas para OpenAI Tool Calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "calculate_interest",
                    "description": "Calculates compound interest for an investment based on principal, annual rate, and years.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "principal": {"type": "number", "description": "The initial capital to invest."},
                            "rate": {"type": "number", "description": "Annual interest rate percentage (e.g., 8 for 8%)."},
                            "years": {"type": "integer", "description": "The investment duration in years."}
                        },
                        "required": ["principal", "rate", "years"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_usd_rate",
                    "description": "Retrieves the current reference exchange rate from USD to COP (US Dollars to Colombian Pesos)."
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_crypto_price",
                    "description": "Fetches the live price of a specific cryptocurrency from CoinGecko API.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "crypto_id": {"type": "string", "description": "The unique ID of the cryptocurrency in lowercase (e.g., 'bitcoin')."},
                            "vs_currency": {"type": "string", "description": "The target fiat currency, defaults to 'usd'."}
                        },
                        "required": ["crypto_id"]
                    }
                }
            }
        ]

    def run(self, session_id: str, text_input: str, base64_image: str = None) -> dict:
        """
        Orquesta la llamada al LLM administrando memoria, capacidades de visión y Tool Calling.
        """
        history = self._get_or_create_memory(session_id)
        content_structure = []
        
        if text_input:
            content_structure.append({"type": "text", "text": text_input})
            
        if base64_image:
            if not base64_image.startswith("data:image"):
                base64_image = f"data:image/jpeg;base64,{base64_image}"
            content_structure.append({
                "type": "image_url",
                "image_url": {"url": base64_image}
            })

        # Almacenar la entrada estructurada en el historial de sesión
        history.append({"role": "user", "content": content_structure})
        self._enforce_memory_limit(session_id)

        # Reconstruir la carga de mensajes inyectando el System Prompt global
        messages_to_send = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages_to_send,
                tools=self._get_tools_definition(),
                tool_choice="auto"
            )

            response_message = response.choices[0].message
            tool_calls = response_message.tool_calls

            # CASO A: Tool Calling activado de forma autónoma
            if tool_calls:
                print(f"[TOOL CALL] El agente invocó: {tool_calls[0].function.name}")
                
                # CORRECCIÓN: Añadir la respuesta intermedia del asistente de forma segura al historial
                history.append(response_message)
                
                tool_output = None
                executed_tool_name = tool_calls[0].function.name
                args = json.loads(tool_calls[0].function.arguments) if tool_calls[0].function.arguments else {}

                if executed_tool_name == "calculate_interest":
                    tool_output = calculate_interest(args.get("principal"), args.get("rate"), args.get("years"))
                elif executed_tool_name == "get_usd_rate":
                    tool_output = get_usd_rate()
                elif executed_tool_name == "get_crypto_price":
                    tool_output = get_crypto_price(args.get("crypto_id"), args.get("vs_currency", "usd"))

                # Añadir el resultado de la ejecución con el ID correspondiente al historial
                history.append({
                    "role": "tool",
                    "tool_call_id": tool_calls[0].id,
                    "name": executed_tool_name,
                    "content": json.dumps(tool_output)
                })

                # Generar la respuesta final combinando el contexto original y el resultado de la herramienta
                second_response = self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history
                )
                
                final_text = second_response.choices[0].message.content
                history.append({"role": "assistant", "content": final_text})
                self._enforce_memory_limit(session_id)

                return {
                    "source": "tool",
                    "sourceName": executed_tool_name,
                    "response": final_text
                }

            # CASO B: Respuesta conversacional o análisis visual regular
            else:
                final_text = response_message.content
                history.append({"role": "assistant", "content": final_text})
                self._enforce_memory_limit(session_id)
                
                return {
                    "source": "llm",
                    "sourceName": None,
                    "response": final_text
                }

        except Exception as e:
            print(f"Error crítico en la ejecución de FinBotAgent: {str(e)}")
            return {
                "source": "error",
                "sourceName": None,
                "response": "Error interno del sistema financiero al procesar la solicitud."
            }