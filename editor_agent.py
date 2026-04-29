"""
editor_agent.py — v2
─────────────────────
Ensambla clips de Veo 3.1 Lite + audio de ElevenLabs en un MP4 final.
Usa MoviePy 2.x para merge de video + audio + captions.
"""

import logging
import os
from pathlib import Path
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

        clips        = task.payload.get("clips", [])
        voiceover    = task.payload.get("voiceover", {})
        product_spec = task.payload.get("product_spec", {})

        output_filename = f"final_video_{self.session_id}.mp4"
        output_path     = os.path.join(self.output_dir, output_filename)

        valid_clips = [c for c in clips if c.get("clip_path") and Path(c["clip_path"]).exists()]

        if not valid_clips:
            logger.warning("[Editor] No hay clips válidos — generando placeholder.")
            result_path = self._generate_placeholder(output_path)
        else:
            logger.info(f"[Editor] Ensamblando {len(valid_clips)} clips de Veo...")
            result_path = self._assemble(valid_clips, voiceover, product_spec, output_path)

        return {
            "video_path":  result_path,
            "title":       product_spec.get("name_es", "UGC Video"),
            "status":      "Ready for TikTok upload",
            "clip_count":  len(valid_clips),
            "has_audio":   bool(voiceover.get("audio_path")),
        }

    def _assemble(self, clips: list, voiceover: dict, product_spec: dict, output_path: str) -> str:
        try:
            from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip, CompositeAudioClip
        except ImportError:
            logger.error("[Editor] MoviePy no instalado. Ejecuta: uv sync")
            return self._generate_placeholder(output_path)

        video_clips = []
        for clip_data in clips:
            clip_path = clip_data["clip_path"]
            try:
                vc = VideoFileClip(clip_path)
                video_clips.append(vc)
                logger.info(f"[Editor] Clip cargado: {clip_path} ({vc.duration:.1f}s)")
            except Exception as e:
                logger.warning(f"[Editor] No se pudo cargar {clip_path}: {e}")

        if not video_clips:
            return self._generate_placeholder(output_path)

        # Concatenar clips
        final_video = concatenate_videoclips(video_clips, method="compose")
        logger.info(f"[Editor] Video concatenado: {final_video.duration:.1f}s total")

        # Agregar audio de ElevenLabs si existe
        audio_path = voiceover.get("audio_path")
        if audio_path and Path(audio_path).exists():
            try:
                vo_audio = AudioFileClip(audio_path)
                # Trim o loop para que no pase de la duración del video
                if vo_audio.duration > final_video.duration:
                    vo_audio = vo_audio.subclipped(0, final_video.duration)
                final_video = final_video.with_audio(vo_audio)
                logger.info(f"[Editor] Audio de ElevenLabs agregado: {audio_path}")
            except Exception as e:
                logger.warning(f"[Editor] No se pudo agregar audio: {e}")

        # Exportar
        final_video.write_videofile(
            output_path,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            logger=None,
        )
        logger.info(f"[Editor] ✅ Video exportado: {output_path}")
        return output_path

    def _generate_placeholder(self, output_path: str) -> str:
        try:
            from moviepy import ColorClip
            clip = ColorClip(size=(1080, 1920), color=[10, 10, 20], duration=5)
            clip.write_videofile(output_path, fps=24, codec="libx264", audio=False, logger=None)
        except Exception as e:
            logger.error(f"[Editor] Placeholder fallido: {e}")
            open(output_path, "w").close()
        return output_path


if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO)
    agent = EditorAgent("editor_01", "dev_session_001")
    agent.start()
    print("EditorAgent v2 corriendo...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
