"""
reviewer_agent_v2.py
────────────────────
Agente 8: El crítico multimodal.
- Analiza el video final MP4 usando Gemini 3.1 Flash / Pro Vision.
- Califica consistencia de Mateo, audio, hooks y timing del tag.
- Devuelve score 0-1 y feedback para reintento.
"""

import json
import logging
import os
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task
from google_clients import GoogleAIApp

logger = logging.getLogger(__name__)

QA_SYSTEM_INSTRUCTION = """
Eres un experto QA de TikTok Ads y TikTok Shop México. 
Analiza el video UGC proporcionado y califica de 0 a 1 en estas 5 dimensiones:

1. **Identidad del Creador**: ¿Es Mateo consistente (barba, gorra NY, tatuaje brazo izquierdo)?
2. **Timing del Tag**: ¿El producto aparece o se menciona prominentemente después del segundo 12? (Penalizar si es antes de los 3s).
3. **Calidad de Audio**: ¿La voz de ElevenLabs suena natural y la mezcla con música es equilibrada?
4. **Hook Visual**: ¿Los primeros 3 segundos capturan la atención sin ser un anuncio obvio?
5. **Estética Mexicana**: ¿Se siente como un video grabado en México (Polanco/Boutique) con estilo premium?

Devuelve ÚNICAMENTE un JSON:
{
  "total_score": 0.85,
  "dimensions": {
     "identity": 0.9,
     "timing": 0.8,
     "audio": 0.9,
     "hook": 0.7,
     "mexican_vibe": 1.0
  },
  "feedback": "Texto detallado del feedback...",
  "approved": true
}
"""

class QAReviewerAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.REVIEWER, session_id)

    def process_task(self, task: Task) -> Any:
        if task.type != "review_final_video":
            raise ValueError(f"Unsupported task type: {task.type}")

        video_path = task.payload.get("video_path")
        if not video_path or not os.path.exists(video_path):
            raise ValueError(f"Video file not found: {video_path}")

        logger.info(f"[QA Reviewer] Analyzing final video: {video_path}")

        try:
            # Enviar video a Gemini Vision
            # Nota: El SDK de Google permite subir archivos grandes o pasar bytes
            raw_response = self._analyze_video_with_vision(video_path)
            
            # Limpiar y parsear JSON
            cleaned = raw_response.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            review_result = json.loads(cleaned)
            
            logger.info(f"[QA Reviewer] ✅ Review completed. Score: {review_result.get('total_score')}")
            return review_result

        except Exception as e:
            logger.error(f"[QA Reviewer] ❌ Review failed: {e}")
            # Fallback score
            return {"total_score": 0.5, "approved": False, "feedback": str(e)}

    def _analyze_video_with_vision(self, video_path: str) -> str:
        """Sube el video a Google AI y obtiene la reseña."""
        from google import genai
        from google.genai import types

        client = GoogleAIApp.get_client()
        
        # 1. Subir el archivo
        logger.info(f"[QA Reviewer] Uploading video to Google AI...")
        with open(video_path, "rb") as f:
            video_bytes = f.read()
            
        # 2. Generar contenido con el video
        response = client.models.generate_content(
            model=GoogleAIApp.get_gemini_2_5_pro(), # Usamos Pro para QA de alta calidad
            contents=[
                types.Part.from_bytes(data=video_bytes, mime_type="video/mp4"),
                types.Part.from_text(text="Realiza la auditoría de este video UGC para TikTok Shop México.")
            ],
            config=types.GenerateContentConfig(
                system_instruction=QA_SYSTEM_INSTRUCTION,
                response_mime_type="application/json"
            )
        )
        
        return response.text
