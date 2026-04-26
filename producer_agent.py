"""
producer_agent.py
─────────────────
Genera imágenes reales por escena usando gemini-3.1-flash-image-preview.
"""

import logging
import os
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task
from google_clients import GoogleAIApp

logger = logging.getLogger(__name__)

IMAGE_MODEL = "gemini-3.1-flash-image-preview"


class ProducerAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.PRODUCER, session_id)
        self.output_dir = os.path.join("output", "images")
        os.makedirs(self.output_dir, exist_ok=True)

    def process_task(self, task: Task) -> Any:
        if task.type == "generate_video":
            return self._generate_scenes(task.payload)
        elif task.type == "generate_image":
            return self._generate_single_image(task.payload)
        else:
            raise ValueError(f"Unsupported task type: {task.type}")

    def _generate_scenes(self, payload: dict) -> dict:
        """Generate one image per scene using Gemini Image model."""
        script = payload.get("script")
        if not script or not isinstance(script, dict):
            logger.warning("No structured script — using generic prompt.")
            script = {
                "title": "AI Video",
                "scenes": [{"scene_number": 1, "visual_prompt": "A futuristic cinematic scene, 9:16 vertical"}]
            }

        scenes = script.get("scenes", [])
        image_paths = []

        for scene in scenes:
            scene_num = scene.get("scene_number", len(image_paths) + 1)
            visual_prompt = scene.get("visual_prompt", "Cinematic scene, dark futuristic aesthetic")
            logger.info(f"Generating image for scene {scene_num}: {visual_prompt[:60]}...")

            try:
                path = self._call_image_model(visual_prompt, scene_num)
                image_paths.append({
                    "scene_number": scene_num,
                    "image_path": path,
                    "duration_seconds": scene.get("duration_seconds", 5),
                    "voiceover": scene.get("voiceover", ""),
                    "caption": scene.get("caption", "")
                })
                logger.info(f"Scene {scene_num} image saved: {path}")
            except Exception as e:
                logger.warning(f"Scene {scene_num} AI generation failed ({e}) — using PIL placeholder.")
                try:
                    path = self._create_placeholder_image(visual_prompt, scene_num)
                    image_paths.append({
                        "scene_number": scene_num,
                        "image_path": path,
                        "duration_seconds": scene.get("duration_seconds", 5),
                        "voiceover": scene.get("voiceover", ""),
                        "caption": scene.get("caption", "")
                    })
                except Exception as e2:
                    logger.error(f"Scene {scene_num} placeholder also failed: {e2}")
                    image_paths.append({
                        "scene_number": scene_num,
                        "image_path": None,
                        "duration_seconds": scene.get("duration_seconds", 5),
                        "voiceover": scene.get("voiceover", ""),
                        "caption": scene.get("caption", "")
                    })

        return {
            "title": script.get("title", "AI Video"),
            "scenes": image_paths
        }

    def _call_image_model(self, prompt: str, scene_num: int) -> str:
        """Generate an image using gemini-3.1-flash-image-preview."""
        from google.genai import types

        client = GoogleAIApp.get_client()

        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=f"Generate a high-quality cinematic 9:16 vertical image: {prompt}",
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"]
            )
        )

        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                img_bytes = part.inline_data.data
                filename = f"scene_{scene_num:02d}_{self.session_id}.png"
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                return filepath

        raise ValueError("No image data returned by model")

    def _create_placeholder_image(self, prompt: str, scene_num: int) -> str:
        """Create a colored placeholder image with PIL as fallback."""
        from PIL import Image, ImageDraw
        import hashlib

        h = hashlib.md5(prompt.encode()).hexdigest()
        r = max(20, int(h[0:2], 16) // 2)
        g = max(20, int(h[2:4], 16) // 2)
        b = max(20, int(h[4:6], 16) // 2)

        img = Image.new("RGB", (1080, 1920), color=(r, g, b))
        draw = ImageDraw.Draw(img)
        draw.text((60, 60), f"Scene {scene_num}", fill=(220, 220, 220))

        words = prompt[:300].split()
        lines, line = [], []
        for word in words:
            line.append(word)
            if len(" ".join(line)) > 40:
                lines.append(" ".join(line[:-1]))
                line = [word]
        lines.append(" ".join(line))

        y = 880
        for text_line in lines[:12]:
            draw.text((60, y), text_line, fill=(255, 255, 255))
            y += 45

        filename = f"scene_{scene_num:02d}_{self.session_id}.png"
        filepath = os.path.join(self.output_dir, filename)
        img.save(filepath)
        return filepath

    def _generate_single_image(self, payload: dict) -> str:
        prompt = payload.get("prompt", "Cinematic scene")
        return self._call_image_model(prompt, 1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import time
    agent = ProducerAgent("producer_01", "dev_session_001")
    agent.start()
    print("Producer Agent running...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
