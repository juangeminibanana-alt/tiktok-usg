import logging
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task

logger = logging.getLogger(__name__)

class ScriptWriterAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.SCRIPTWRITER, session_id)

    def process_task(self, task: Task) -> Any:
        product_spec = task.payload.get("product_spec", {})
        prompt = (
            f"Eres un experto guionista de TikTok Shop. Escribe un guion para:\n"
            f"Producto: {product_spec.get('name_es')}\n"
            f"Precio: ${product_spec.get('price_current')} MXN\n"
            f"Responde solo en JSON con: 'hook', 'body', 'cta' y 'text_overlays' (lista de 6 frases)."
        )
        return self.generate_content(prompt, model="gemini-1.5-flash", is_json=True)
