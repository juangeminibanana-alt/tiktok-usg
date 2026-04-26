"""
google_clients.py — VERSIÓN ACTUALIZADA 2026
────────────────────────────────────────
Fix: veo-3.1-lite-generate-preview (string corregido)
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
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

            if api_key:
                logger.info("Initializing Google Gen AI Client with API Key.")
                cls._client = genai.Client(api_key=api_key)
            elif project:
                logger.info(f"Initializing via Vertex AI (Project: {project}).")
                cls._client = genai.Client(vertexai=True, project=project, location=location)
            else:
                cls._client = genai.Client(vertexai=True)

        return cls._client

    @staticmethod
    def get_gemini_2_0_flash():
        return "gemini-3.1-flash-lite-preview"

    @staticmethod
    def get_gemini_2_5_pro():
        return "gemini-3.1-pro-preview"

    @staticmethod
    def get_gemini_flash_lite():
        return "gemini-3.1-flash-lite-preview"

    @staticmethod
    def get_nano_banana_2():
        """Nano Banana 2 — generación de imágenes con face-match."""
        return "gemini-3.1-flash-image-preview"

    @staticmethod
    def get_nano_banana_pro():
        """Nano Banana Pro — mayor fidelidad de identidad."""
        return "gemini-3.1-pro-image-preview"

    @staticmethod
    def get_veo_3_1_lite():
        """Veo 3.1 Lite — generación de video image-to-video. ✅ CORREGIDO."""
        return "veo-3.1-lite-generate-preview"

    @staticmethod
    def get_veo_3_1_generate_preview():
        """Alias para compatibilidad con código existente."""
        return "veo-3.1-lite-generate-preview"
