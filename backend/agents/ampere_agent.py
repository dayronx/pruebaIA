import os
import json
import httpx
from openai import OpenAI
from dotenv import load_dotenv

# Importaciones de tu proyecto
from backend.agents.prompts import SYSTEM_PROMPT
from backend.tools.electrical_tools import ohms_law, watts_law, unit_convert
from backend.services.scraper_service import ScraperService

load_dotenv()

class AmpereBotAgent:
    def __init__(self):
        # CONFIGURACIÓN CORREGIDA PARA OPENAI
        # verify=False ayuda a evitar el error 421 Misdirected Request en redes con firewall (RIWI)
        self.client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            http_client=httpx.Client(
                verify=False,
                timeout=30.0
            )
        )
        self.sessions_memory = {}

    def _get_or_create_memory(self, session_id: str) -> list:
        if session_id not in self.sessions_memory:
            self.sessions_memory[session_id] = []
        return self.sessions_memory[session_id]

    def _enforce_memory_limit(self, session_id: str):
        if len(self.sessions_memory[session_id]) > 14:
            self.sessions_memory[session_id] = self.sessions_memory[session_id][-14:]

    def _get_tools_definition(self) -> list:
        return [
            {
                "type": "function",
                "function": {
                    "name": "ohms_law",
                    "description": "Calcula Voltaje, Corriente o Resistencia.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "voltage": {"type": "number"}, "current": {"type": "number"}, "resistance": {"type": "number"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "technical_search",
                    "description": "Busca conceptos técnicos en la base de datos.",
                    "parameters": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}}
                    }
                }
            }
        ]

    def run(self, session_id: str, text_input: str, base64_image: str = None) -> dict:
        history = self._get_or_create_memory(session_id)
        content = [{"type": "text", "text": text_input}]
        
        history.append({"role": "user", "content": content})
        self._enforce_memory_limit(session_id)

        try:
            # Llamada a OpenAI (usando gpt-4o o gpt-4o-mini)
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history,
                tools=self._get_tools_definition(),
                tool_choice="auto"
            )

            msg = response.choices[0].message
            
            # Lógica de herramientas simplificada
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                history.append(msg)
                tool_call = msg.tool_calls[0]
                args = json.loads(tool_call.function.arguments)
                
                res = None
                if tool_call.function.name == "ohms_law":
                    res = ohms_law(**args)
                elif tool_call.function.name == "technical_search":
                    res = ScraperService().search_chunks(args.get("query"))
                
                history.append({"role": "tool", "tool_call_id": tool_call.id, "content": json.dumps(res)})

                final_res = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "system", "content": SYSTEM_PROMPT}] + history
                )
                final_text = final_res.choices[0].message.content
            else:
                final_text = msg.content

            history.append({"role": "assistant", "content": final_text})
            return {"source": "llm", "response": final_text}

        except Exception as e:
            print(f"ERROR CRÍTICO: {e}")
            return {"source": "error", "response": "Error de conexión con OpenAI. Revisa tu red."}