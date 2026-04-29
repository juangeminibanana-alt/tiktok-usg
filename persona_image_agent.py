import logging
import os
import base64
from pathlib import Path
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task
from google_clients import GoogleAIApp

logger = logging.getLogger(__name__)

IMAGE_MODEL = "gemini-3.1-flash-image-preview"

MASTER_IDENTITY = (
    "Juan, a 32-year-old Mexican man, robust build approximately 1.80m tall "
    "and 110kg, broad shoulders and full chest, warm morena skin tone, "
    "full thick well-groomed black beard with crisp definition, short dark hair "
    "completely hidden under a black New Era New York Yankees cap worn straight, "
    "calm confident expression with intense dark eyes, large detailed black-and-grey "
    "realism tattoo sleeve covering his left forearm visible from elbow to wrist."
)

NEGATIVE_UNIVERSAL = (
    "no deformed hands, no extra fingers, no warped face, no double face, "
    "no face morph, no other people in frame, no readable brand text except NY cap, "
    "no text overlay, no watermark, no warped mirror reflection, "
    "no plastic skin, anatomically correct hands and limbs, no cartoon, no anime"
)

SHOT_DEFINITIONS = [
    {
        "shot_number": 1,
        "name": "hook_texture",
        "duration_seconds": 5,
        "description": "Macro extremo de la textura del ante",
        "prompt": (
            "Ultra macro close-up shot of premium caramel-colored faux suede jacket fabric. "
            "Fabric texture is the hero. Soft studio lighting. Hasselblad 120mm macro. 9:16 vertical."
        ),
        "veo_motion_prompt": "Slow creeping macro dolly-in toward fabric texture. 5 seconds."
    },
    {
        "shot_number": 2,
        "name": "mirror_reveal",
        "duration_seconds": 8,
        "description": "Mirror selfie reveal",
        "prompt": (
            f"{MASTER_IDENTITY} Standing in front of a mirror in a modern boutique. "
            "Taking a selfie with a smartphone. Wearing the caramel suede jacket. 9:16 vertical."
        ),
        "veo_motion_prompt": "Subtle handheld sway. Subject shifts weight. 8 seconds."
    },
    {
        "shot_number": 3,
        "name": "zipper_macro",
        "duration_seconds": 5,
        "description": "Macro del cierre",
        "prompt": (
            f"{MASTER_IDENTITY} Extreme close-up of hands pulling the jacket zipper. "
            "Caramel suede background. 9:16 vertical."
        ),
        "veo_motion_prompt": "Hands slowly pull zipper down then up. 5 seconds."
    },
    {
        "shot_number": 4,
        "name": "mirror_adjustment",
        "duration_seconds": 5,
        "description": "Ajustando solapas",
        "prompt": (
            f"{MASTER_IDENTITY} Medium shot adjusting jacket lapels in the mirror. "
            "Confidence. 9:16 vertical."
        ),
        "veo_motion_prompt": "Precise lapel adjustments. Slow push-in. 5 seconds."
    },
    {
        "shot_number": 5,
        "name": "walking_boutique",
        "duration_seconds": 5,
        "description": "Walking shot",
        "prompt": (
            f"{MASTER_IDENTITY} Full body walking toward camera in boutique. "
            "Caramel suede jacket. 9:16 vertical."
        ),
        "veo_motion_prompt": "Walks at relaxed pace toward camera. 5 seconds."
    },
    {
        "shot_number": 6,
        "name": "hero_product_cta",
        "duration_seconds": 5,
        "description": "Product hero shot",
        "prompt": (
            "Studio product photography of the jacket on a mannequin. "
            "Pure black background. 9:16 vertical."
        ),
        "veo_motion_prompt": "Very slow 30 degree rotation. 5 seconds."
    }
]

class PersonaImageAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str, character_pack_dir: str = "character_pack"):
        super().__init__(agent_id, AgentRole.PERSONA_IMAGE, session_id)
        self.character_pack_dir = character_pack_dir
        self.output_dir = os.path.join("output", "frames")
        os.makedirs(self.output_dir, exist_ok=True)

    def process_task(self, task: Task) -> Any:
        product_spec = task.payload.get("product_spec", {})
        reference_images = self._load_character_pack()
        frames = []
        for shot_def in SHOT_DEFINITIONS:
            try:
                frame_path = self._generate_frame(shot_def, reference_images, product_spec)
                frames.append({
                    "shot_number": shot_def["shot_number"],
                    "name": shot_def["name"],
                    "frame_path": frame_path,
                    "duration_seconds": shot_def["duration_seconds"],
                    "veo_motion_prompt": shot_def["veo_motion_prompt"]
                })
            except Exception as e:
                logger.error(f"Error shot {shot_def['shot_number']}: {e}")
        return {"frames": frames}

    def _load_character_pack(self) -> list:
        pack_dir = Path(self.character_pack_dir)
        reference_images = []
        if pack_dir.exists():
            for filepath in sorted(pack_dir.iterdir())[:4]:
                if filepath.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    with open(filepath, "rb") as f:
                        img_bytes = f.read()
                    reference_images.append({
                        "data": base64.b64encode(img_bytes).decode(),
                        "mime_type": "image/png" if filepath.suffix == ".png" else "image/jpeg"
                    })
        return reference_images

    def _generate_frame(self, shot_def: dict, reference_images: list, product_spec: dict) -> str:
        from google.genai import types
        client = GoogleAIApp.get_client()
        contents = []
        for ref in reference_images:
            contents.append(types.Part.from_bytes(data=base64.b64decode(ref["data"]), mime_type=ref["mime_type"]))
        prompt = shot_def["prompt"]
        contents.append(types.Part.from_text(text=prompt))
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="9:16", image_size="2K")
            )
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                filepath = os.path.join(self.output_dir, f"shot_{shot_def['shot_number']:02d}_{self.session_id}.png")
                with open(filepath, "wb") as f:
                    f.write(part.inline_data.data)
                return filepath
        raise ValueError("No image returned")
