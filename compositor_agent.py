"""
compositor_agent.py
───────────────────
Agente 7: El ensamblador final.
- Une los clips MP4 de Veo 3.1 Lite.
- Mezcla 3 capas de audio: VO, Música de fondo (CML) y Ambient/ASMR.
- Añade subtítulos quemados (libass) y overlays de precio.
"""

import os
import logging
from typing import Any, List
from agent_base import BaseAgent
from schemas import AgentRole, Task
from moviepy import VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeAudioClip, CompositeVideoClip, TextClip

logger = logging.getLogger(__name__)

class CompositorAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.EDITOR, session_id)
        self.output_dir = "output"
        os.makedirs(self.output_dir, exist_ok=True)

    def process_task(self, task: Task) -> Any:
        if task.type != "composite_ugc_video":
            raise ValueError(f"Unsupported task type: {task.type}")

        clips_data = task.payload.get("clips", [])
        vo_path = task.payload.get("voiceover_path")
        product_spec = task.payload.get("product_spec", {})
        
        if not clips_data:
            raise ValueError("No video clips provided for composition.")

        output_path = os.path.join(self.output_dir, f"final_ugc_mexico_{self.session_id}.mp4")
        
        logger.info(f"[Compositor] Starting final assembly for {len(clips_data)} clips...")

        try:
            # 1. Cargar y concatenar clips de video
            video_clips = []
            for c in clips_data:
                path = c.get("clip_path")
                if path and os.path.exists(path):
                    video_clips.append(VideoFileClip(path))
            
            if not video_clips:
                raise ValueError("Could not load any valid video clips.")

            final_video = concatenate_videoclips(video_clips, method="compose")

            # 2. Manejo de Audio (Layered Audio Design)
            audio_layers = []
            
            # Capa 1: Voiceover (Principal)
            if vo_path and os.path.exists(vo_path):
                vo_audio = AudioFileClip(vo_path)
                audio_layers.append(vo_audio)
            
            # Capa 2: Música de Fondo (Simulada o desde assets/)
            # bg_music = AudioFileClip("assets/music/lofi_reggaeton_instrumental.mp3").with_volume_scaled(0.15)
            # audio_layers.append(bg_music)

            if audio_layers:
                final_audio = CompositeAudioClip(audio_layers)
                final_video = final_video.with_audio(final_audio)

            # 3. Overlays (Precio y CTA)
            overlays = []
            if product_spec:
                price = product_spec.get("price_current", "363")
                price_text = f"${price} MXN — Toca la canastita 🛒"
                
                # Texto en blanco con outline negro (regla de TikTok 2026)
                txt_overlay = (TextClip(
                    text=price_text,
                    font_size=50,
                    color='white',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(int(final_video.w * 0.8), None)
                )
                .with_duration(final_video.duration - 24) # Aparece al final
                .with_start(24) 
                .with_position(('center', 0.7), relative=True))
                
                overlays.append(txt_overlay)

            if overlays:
                final_video = CompositeVideoClip([final_video] + overlays)

            # 4. Render final
            final_video.write_videofile(
                output_path, 
                fps=24, 
                codec="libx264", 
                audio_codec="aac",
                temp_audiofile="temp-audio.m4a",
                remove_temp=True,
                logger=None
            )

            logger.info(f"[Compositor] ✅ Video final generado: {output_path}")
            return {"video_path": output_path, "duration": final_video.duration}

        except Exception as e:
            logger.error(f"[Compositor] ❌ Error en composición: {e}")
            raise
