"""
veo_generator_agent.py
──────────────────────
Agente 5: Genera clips de video reales con Veo 3.1 Lite.
- Recibe frames de PersonaImageAgent + motion prompts
- Genera un clip MP4 por shot via image-to-video
- Descarga y guarda los clips antes de que expiren (48h)
"""

import logging
import os
import time
from pathlib import Path
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task
from google_clients import GoogleAIApp

logger = logging.getLogger(__name__)

VEO_MODEL = "veo-3.1-lite-generate-preview"


class VeoGeneratorAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.VEO_GENERATOR, session_id)

        self.output_dir = os.path.join("output", "clips")
        os.makedirs(self.output_dir, exist_ok=True)

    def process_task(self, task: Task) -> Any:
        if task.type != "generate_clips":
            raise ValueError(f"Unsupported task type: {task.type}")

        frames_data = task.payload.get("frames", [])
        if not frames_data:
            raise ValueError("No frames provided")

        logger.info(f"[VeoGenerator] Generating {len(frames_data)} clips with Veo 3.1 Lite")

        clips = []
        for frame in frames_data:
            frame_path = frame.get("frame_path")
            if not frame_path or not Path(frame_path).exists():
                logger.warning(f"[VeoGenerator] Skipping shot {frame.get('shot_number')} — no frame")
                continue

            shot_num = frame.get("shot_number", 0)
            motion_prompt = frame.get("veo_motion_prompt", "")
            duration = frame.get("duration_seconds", 5)
            # Veo 3.1 Lite requires EXACTLY 8s for 1080p
            veo_duration = 8

            logger.info(f"[VeoGenerator] Generating clip for shot {shot_num} (Forced 8s for 1080p)...")

            try:
                clip_path = self._generate_clip(
                    frame_path=frame_path,
                    prompt=motion_prompt,
                    duration=veo_duration,
                    shot_num=shot_num
                )
                clips.append({
                    "shot_number": shot_num,
                    "name": frame.get("name", ""),
                    "clip_path": clip_path,
                    "duration_seconds": veo_duration,
                    "voiceover_text": frame.get("voiceover_text", "")
                })
                logger.info(f"[VeoGenerator] ✅ Clip {shot_num} saved: {clip_path}")

            except Exception as e:
                logger.error(f"[VeoGenerator] ❌ Clip {shot_num} failed: {e}")
                clips.append({
                    "shot_number": shot_num,
                    "clip_path": None,
                    "error": str(e)
                })

        return {
            "clips": clips,
            "total": len(clips),
            "successful": sum(1 for c in clips if c.get("clip_path"))
        }

    def _generate_clip(self, frame_path: str, prompt: str, duration: int, shot_num: int) -> str:
        """Genera un clip real con Veo 3.1 Lite via image-to-video."""
        from google import genai
        from google.genai import types

        client = GoogleAIApp.get_client()

        # Load starting frame
        with open(frame_path, "rb") as f:
            image_bytes = f.read()

        mime = "image/png" if frame_path.endswith(".png") else "image/jpeg"
        start_image = types.Image(image_bytes=image_bytes, mime_type=mime)

        logger.info(f"[VeoGenerator] Submitting shot {shot_num} to Veo 3.1 Lite...")

        operation = client.models.generate_videos(
            model=VEO_MODEL,
            prompt=prompt,
            image=start_image,
            config=types.GenerateVideosConfig(
                aspect_ratio="9:16",
                resolution="1080p",
                duration_seconds=duration,
                person_generation="allow_adult",
            ),
        )

        # Poll until done (typically 2-5 minutes)
        logger.info(f"[VeoGenerator] Waiting for Veo to complete shot {shot_num}...")
        poll_interval = 15
        max_wait = 600  # 10 minutes max

        elapsed = 0
        while not operation.done:
            time.sleep(poll_interval)
            elapsed += poll_interval
            operation = client.operations.get(operation)
            logger.info(f"[VeoGenerator] Shot {shot_num} — {elapsed}s elapsed, still processing...")
            if elapsed >= max_wait:
                raise TimeoutError(f"Veo timeout after {max_wait}s for shot {shot_num}")

        # Download video — expires in 48 hours!
        if not operation.response or not operation.response.generated_videos:
            raise ValueError(f"Veo completed but returned no video for shot {shot_num}. Response: {operation.response}")
            
        video = operation.response.generated_videos[0]
        client.files.download(file=video.video)

        filename = f"clip_{shot_num:02d}_{self.session_id}.mp4"
        filepath = os.path.join(self.output_dir, filename)
        video.video.save(filepath)

        logger.info(f"[VeoGenerator] ✅ Shot {shot_num} downloaded: {filepath}")
        return filepath


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import time
    agent = VeoGeneratorAgent("veo_01", "dev_session_001")
    agent.start()
    print("VeoGeneratorAgent running...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
