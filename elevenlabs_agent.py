"""
elevenlabs_agent.py
───────────────────
Agente 6: Genera la voz en off en español con ElevenLabs Eleven v3.
- Recibe el script con audio tags emocionales
- Genera MP3 con voz clonada de Juan
- Devuelve audio + timestamps para sincronización
"""

import base64
import json
import logging
import os
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task

logger = logging.getLogger(__name__)

# Script de voz en off para la chamarra de ante café
# Audio tags de ElevenLabs v3: [excited], [whispers], [pauses], [confident]
VOICEOVER_SCRIPT = """[excited] Atención, esta chamarra lo tiene todo.
Ante sintético premium... [pauses] que parece cuero de verdad.
Cuello con solapa estructurada... cremallera completa... [whispers] y la tela más gruesa que he tocado.
[confident] Disponible desde talla S hasta XXL.
Antes costaba $757... hoy en TikTok Shop la consigues en $363.
[excited] Más de la mitad de descuento. Toca la canastita amarilla."""


class ElevenLabsAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.ELEVENLABS, session_id)

        self.output_dir = os.path.join("output", "audio")
        os.makedirs(self.output_dir, exist_ok=True)
        self.api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        self.voice_id = os.environ.get("ELEVENLABS_VOICE_ID", "")

    def process_task(self, task: Task) -> Any:
        if task.type != "generate_voiceover":
            raise ValueError(f"Unsupported task type: {task.type}")

        script = task.payload.get("script", VOICEOVER_SCRIPT)
        voice_id = task.payload.get("voice_id", self.voice_id)
        target_duration = task.payload.get("target_duration_seconds", 28)

        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY not set in environment")
        if not voice_id:
            raise ValueError("ELEVENLABS_VOICE_ID not set — clone your voice first at elevenlabs.io")

        logger.info(f"[ElevenLabs] Generating voiceover — target: {target_duration}s")

        try:
            from elevenlabs.client import ElevenLabs
            client = ElevenLabs(api_key=self.api_key)

            response = client.text_to_speech.convert_with_timestamps(
                voice_id=voice_id,
                text=script,
                model_id="eleven_v3",
                language_code="es",
                output_format="mp3_44100_128",
                voice_settings={
                    "stability": 0.35,
                    "similarity_boost": 0.80,
                    "style": 0.25,
                    "use_speaker_boost": True,
                    "speed": 1.05,
                },
            )

            # Save audio
            audio_bytes = base64.b64decode(response.audio_base64)
            filename = f"voiceover_{self.session_id}.mp3"
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, "wb") as f:
                f.write(audio_bytes)

            # Parse timestamps for sync
            alignment = response.alignment
            word_times = self._extract_word_times(alignment)

            logger.info(f"[ElevenLabs] ✅ Voiceover saved: {filepath}")
            logger.info(f"[ElevenLabs] Word timestamps: {len(word_times)} words")

            return {
                "audio_path": filepath,
                "duration_seconds": word_times[-1]["end"] if word_times else 0,
                "word_timestamps": word_times,
                "script": script,
                "voice_id": voice_id
            }

        except ImportError:
            logger.error("[ElevenLabs] elevenlabs package not installed. Run: pip install elevenlabs")
            raise
        except Exception as e:
            logger.error(f"[ElevenLabs] Error: {e}")
            raise

    def _extract_word_times(self, alignment) -> list:
        """Convierte timestamps de carácter-nivel a palabra-nivel."""
        if not alignment:
            return []

        words = []
        chars = alignment.characters or []
        starts = alignment.character_start_times_seconds or []
        ends = alignment.character_end_times_seconds or []

        current_word = ""
        word_start = 0.0

        for i, (char, start, end) in enumerate(zip(chars, starts, ends)):
            if char in (" ", "\n", "\t") or i == len(chars) - 1:
                if i == len(chars) - 1 and char not in (" ", "\n"):
                    current_word += char
                if current_word.strip():
                    words.append({
                        "word": current_word.strip(),
                        "start": round(word_start, 3),
                        "end": round(end, 3)
                    })
                current_word = ""
                word_start = end
            else:
                if not current_word:
                    word_start = start
                current_word += char

        return words


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import time
    agent = ElevenLabsAgent("elevenlabs_01", "dev_session_001")
    agent.start()
    print("ElevenLabsAgent running...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
