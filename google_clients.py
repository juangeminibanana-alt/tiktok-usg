"""
google_clients.py
─────────────────
Modernized Factory for Google Gen AI SDK (google-genai).
Handles initialization for both standard Gemini API and Vertex AI.
"""

import os
import logging
from dotenv import load_dotenv
from google import genai

# Load environment variables from .env if present
load_dotenv()

logger = logging.getLogger(__name__)

class GoogleAIApp:
    """
    Singleton-like Factory for initializing and retrieving Google AI clients.
    Automatically switches between Gemini API and Vertex AI based on credentials.
    """
    _client = None

    @classmethod
    def get_client(cls) -> genai.Client:
        """Returns the shared genai.Client instance."""
        if cls._client is None:
            api_key = os.environ.get("GOOGLE_API_KEY")
            project = os.environ.get("GOOGLE_CLOUD_PROJECT")
            location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

            # Initialization logic for the new SDK
            if api_key:
                logger.info("Initializing Google Gen AI Client with API Key.")
                cls._client = genai.Client(api_key=api_key)
            elif project:
                logger.info(f"Initializing Google Gen AI Client via Vertex AI (Project: {project}).")
                cls._client = genai.Client(vertexai=True, project=project, location=location)
            else:
                # Fallback to default auth (ADC)
                logger.info("Initializing Google Gen AI Client via Application Default Credentials (ADC).")
                cls._client = genai.Client(vertexai=True)
        
        return cls._client

    @staticmethod
    def get_gemini_2_0_flash():
        """Returns the current Flash model (using Lite for better availability)."""
        return "gemini-3.1-flash-lite-preview"

    @staticmethod
    def get_gemini_2_5_pro():
        """Returns the current Pro model (gemini-3.1-pro-preview)."""
        return "gemini-3.1-pro-preview"

    @staticmethod
    def get_gemini_flash_lite():
        """Returns the lite model for high-volume, simple tasks."""
        return "gemini-3.1-flash-lite-preview"

    @staticmethod
    def get_gemini_3_pro_image_preview():
        """Returns gemini-3-pro-image-preview (Imagen 3 / Gemini 2.0 style)."""
        # In the new SDK, we often use 'imagen-3' or similar for generation
        return "imagen-3.0-generate-001"

    @staticmethod
    def get_veo_client():
        """Returns the shared client for Veo (Video generation)."""
        return GoogleAIApp.get_client()

    @staticmethod
    def get_veo_3_1_generate_preview():
        """Returns the veo-3.1-generate-preview model reference."""
        return "veo-2.0-generate-001" # Using current available naming pattern
