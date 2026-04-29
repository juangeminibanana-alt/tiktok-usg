"""
google_clients.py — v2
──────────────────────
Factory para Google Gen AI SDK (google-genai).
Modelos actualizados y verificados en Google AI Studio abril 2026.
"""

import os
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()
logger = logging.getLogger(__name__)


class GoogleAIApp:
    _client = None

    @classmethod
    def get_client(cls) -> genai.Client:
        if cls._client is None:
            api_key = os.environ.get("GOOGLE_API_KEY")
            project  = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

            if api_key:
                logger.info("Google Gen AI ← API Key")
                cls._client = genai.Client(api_key=api_key)
            elif project:
                logger.info(f"Google Gen AI ← Vertex AI ({project})")
                cls._client = genai.Client(vertexai=True, project=project, location=location)
            else:
                logger.info("Google Gen AI ← ADC")
                cls._client = genai.Client(vertexai=True)

        return cls._client

    # ── Modelos de texto ───────────────────────────────────────────────────────
    @staticmethod
    def get_gemini_flash_lite() -> str:
        """Tareas de alto volumen y bajo costo."""
        return "gemini-3.1-flash-lite-preview"

    @staticmethod
    def get_gemini_2_0_flash() -> str:
        return "gemini-3.1-flash-lite-preview"

    @staticmethod
    def get_gemini_flash() -> str:
        return "gemini-3.1-flash-preview"

    @staticmethod
    def get_gemini_2_5_pro() -> str:
        """Máxima calidad de razonamiento."""
        return "gemini-3.1-pro-preview"

    # ── Modelos de imagen ──────────────────────────────────────────────────────
    @staticmethod
    def get_nano_banana_2() -> str:
        """Nano Banana 2 — generación de imágenes con face-match. ✅ Verificado."""
        return "gemini-3.1-flash-image-preview"

    @staticmethod
    def get_nano_banana_pro() -> str:
        """Nano Banana Pro — máxima fidelidad de identidad."""
        return "gemini-3.1-pro-image-preview"

    # ── Modelo de video ────────────────────────────────────────────────────────
    @staticmethod
    def get_veo_3_1_lite() -> str:
        """Veo 3.1 Lite — image-to-video 9:16. ✅ Verificado en AI Studio."""
        return "veo-3.1-lite-generate-preview"

    @staticmethod
    def get_veo_3_1_generate_preview() -> str:
        """Alias para compatibilidad."""
        return "veo-3.1-lite-generate-preview"

    # ── Helper para BaseAgent.get_model() ─────────────────────────────────────
    @classmethod
    def resolve(cls, hint: str) -> str:
        """Resuelve un hint de modelo a su string real."""
        h = hint.lower()
        if "pro"   in h: return cls.get_gemini_2_5_pro()
        if "lite"  in h: return cls.get_gemini_flash_lite()
        if "flash" in h: return cls.get_gemini_flash_lite()
        if "veo"   in h: return cls.get_veo_3_1_lite()
        if "image" in h: return cls.get_nano_banana_2()
        return cls.get_gemini_flash_lite()
