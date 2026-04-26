"""
editor_agent.py
───────────────
Ensambla imágenes generadas en un video MP4 real usando MoviePy.
"""

import logging
import os
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task

logger = logging.getLogger(__name__)


class EditorAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.EDITOR, session_id)
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

    def process_task(self, task: Task) -> Any:
        if task.type != "assemble_video":
            raise ValueError(f"Unsupported task type: {task.type}")

        assets = task.payload.get("assets", [])
        if not assets:
            raise ValueError("No assets provided to assemble.")

        asset_data = assets[0] if assets else {}
        scenes = asset_data.get("scenes", []) if isinstance(asset_data, dict) else []
        title = asset_data.get("title", "AI Video") if isinstance(asset_data, dict) else "AI Video"

        output_filename = f"final_video_{self.session_id}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)

        if scenes and any(s.get("image_path") for s in scenes):
            logger.info(f"Assembling REAL video from {len(scenes)} scenes...")
            result_path = self._assemble_with_moviepy(scenes, output_path)
        else:
            logger.warning("No valid image paths found — generating placeholder video.")
            result_path = self._generate_placeholder(output_path)

        logger.info(f"Video assembled: {result_path}")
        return {
            "video_path": result_path,
            "title": title,
            "status": "Ready for upload",
            "scene_count": len(scenes)
        }

    def _assemble_with_moviepy(self, scenes: list, output_path: str) -> str:
        """Stitch scene images into a real MP4 using MoviePy 2.x."""
        try:
            from moviepy import ImageClip, concatenate_videoclips, TextClip, CompositeVideoClip
        except ImportError:
            logger.error("MoviePy not installed. Run: uv sync")
            return self._generate_placeholder(output_path)

        clips = []
        for scene in scenes:
            image_path = scene.get("image_path")
            duration = scene.get("duration_seconds", 5)
            caption = scene.get("caption", "")

            if not image_path or not os.path.exists(image_path):
                logger.warning(f"Missing image for scene {scene.get('scene_number')} — skipping.")
                continue

            try:
                # MoviePy 2.x: duration in constructor, no set_fps needed
                clip = ImageClip(image_path, duration=duration)

                # Add caption overlay if available
                if caption:
                    try:
                        txt = (
                            TextClip(
                                text=caption,
                                font_size=40,
                                color='white',
                                stroke_color='black',
                                stroke_width=2,
                                size=(clip.w, None),
                                method='caption',
                                duration=duration,
                            )
                            .with_position(('center', 'bottom'))
                        )
                        clip = CompositeVideoClip([clip, txt])
                    except Exception as e:
                        logger.warning(f"Could not add caption: {e}")

                clips.append(clip)
            except Exception as e:
                logger.error(f"Error creating clip for scene: {e}")
                continue

        if not clips:
            return self._generate_placeholder(output_path)

        final = concatenate_videoclips(clips, method="compose")
        final.write_videofile(output_path, fps=24, codec="libx264", audio=False, logger=None)
        return output_path

    def _generate_placeholder(self, output_path: str) -> str:
        """Generate a simple placeholder video with a black background."""
        try:
            from moviepy import ColorClip
            clip = ColorClip(size=(1080, 1920), color=[10, 10, 20], duration=5)
            clip.write_videofile(output_path, fps=24, codec="libx264", audio=False, logger=None)
        except Exception as e:
            logger.error(f"Placeholder generation failed: {e}")
            # Create empty file as last resort
            open(output_path, 'w').close()
        return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import time
    agent = EditorAgent("editor_01", "dev_session_001")
    agent.start()
    print("Editor Agent running...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
