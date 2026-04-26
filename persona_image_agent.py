"""
persona_image_agent.py
──────────────────────
Agente 3: Genera imágenes de Juan (el creador) vistiendo la prenda.
- Recibe ProductSpec + CharacterPack (fotos de referencia de Juan)
- Usa Nano Banana 2 (gemini-3.1-flash-image-preview) con face-match
- Genera 6 frames 9:16 para alimentar a Veo 3.1 Lite
- Cada frame corresponde a un shot del storyboard
"""

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

# ── Master Identity String — NUNCA parafrasear, copiar verbatim ────────────────
MASTER_IDENTITY = (
    "Juan, a 32-year-old Mexican man, robust build approximately 1.80m tall "
    "and 110kg, broad shoulders and full chest, warm morena skin tone, "
    "full thick well-groomed black beard with crisp definition, short dark hair "
    "completely hidden under a black New Era New York Yankees cap worn straight, "
    "calm confident expression with intense dark eyes, large detailed black-and-grey "
    "realism tattoo sleeve covering his left forearm visible from elbow to wrist."
)

# ── Negative prompt universal ──────────────────────────────────────────────────
NEGATIVE_UNIVERSAL = (
    "no deformed hands, no extra fingers, no warped face, no double face, "
    "no face morph, no other people in frame, no readable brand text except NY cap, "
    "no text overlay, no watermark, no warped mirror reflection, "
    "no plastic skin, anatomically correct hands and limbs, no cartoon, no anime"
)

# ── Shot definitions para chamarra de ante café ────────────────────────────────
SHOT_DEFINITIONS = [
    {
        "shot_number": 1,
        "name": "hook_texture",
        "duration_seconds": 5,
        "description": "Macro extremo de la textura del ante — HOOK visual sin mostrar a Juan",
        "prompt": (
            "Ultra macro close-up shot of premium caramel-colored faux suede jacket fabric, "
            "filling the entire 9:16 frame. Fabric texture is the hero — every fiber, pore and "
            "weave visible in stunning detail. Soft studio lighting with warm tungsten key from "
            "upper-right creating micro-shadows in the texture. One gloved hand at the bottom "
            "edge gently pinching the fabric to show its thickness and quality. "
            "Background: pure matte black. No face visible. "
            "Shot on Hasselblad medium format, 120mm macro, f/4, Kodak Portra 400. "
            "Photorealistic editorial style. 9:16 vertical. "
            f"Negative: {NEGATIVE_UNIVERSAL}"
        ),
        "veo_motion_prompt": (
            "Slow creeping macro dolly-in toward fabric texture, 0.3cm/sec forward movement. "
            "Fabric ripples very subtly as gloved fingers gently release pinch in slow motion. "
            "Micro-particles of faux suede fiber catch the light. "
            "5 seconds."
        )
    },
    {
        "shot_number": 2,
        "name": "mirror_reveal",
        "description": "Mirror selfie reveal — Juan frente al espejo en boutique con la chamarra puesta",
        "duration_seconds": 8,
        "prompt": (
            f"{MASTER_IDENTITY} "
            "Standing in front of a large rectangular mirror with matte black frame in a modern "
            "Mexican menswear boutique in Polanco. He is taking a mirror selfie with his iPhone, "
            "phone held at chest height partially covering his lower face — eyes, beard line, "
            "and NY Yankees cap remain clearly visible. "
            "Wearing the caramel faux suede collared jacket over a plain black fitted tee, "
            "black slim-fit trousers, black Chelsea boots. Left arm at side showing tattoo sleeve. "
            "Boutique background: warm cream walls, walnut wood paneling, brushed brass clothing "
            "rail with 3 garments softly out of focus, polished concrete floor. "
            "Lighting: warm 3200K tungsten pendant from upper right, cool daylight fill from "
            "storefront window camera-left, subtle fill on face. "
            "iPhone 15 Pro selfie perspective, 24mm f/1.8. GQ Mexico x Mr Porter editorial mood. "
            "Kodak Portra 400 color grade. Photorealistic. 9:16 vertical. 2K resolution. "
            f"Negative: {NEGATIVE_UNIVERSAL}"
        ),
        "veo_motion_prompt": (
            "Animate the attached starting frame. Camera: locked with 0.5° handheld smartphone "
            "sway mimicking natural selfie hold. Juan subtly shifts weight right-to-left leg, "
            "chest rises with natural breathing, half-smile deepens into confident smirk. "
            "Jacket fabric ripples gently at shoulders. Left hand relaxes drawing eye to tattoo. "
            "NO talking, NO mouth movement, NO head turning. "
            "8 seconds, 9:16, 1080p."
        )
    },
    {
        "shot_number": 3,
        "name": "zipper_macro",
        "description": "Macro del cierre — manos de Juan jalando la cremallera lentamente",
        "duration_seconds": 5,
        "prompt": (
            f"{MASTER_IDENTITY} "
            "Extreme close-up macro shot framing only Juan's hands and the jacket's full-length "
            "zipper, from chest to waist level. His LEFT hand — with tattoo sleeve visible at "
            "wrist — grips the zipper pull while his right hand steadies the jacket hem. "
            "The caramel faux suede jacket fills the frame background. "
            "The YKK-style zipper teeth are crisp and detailed. Warm studio lighting. "
            "Shot on 85mm macro, shallow depth of field, Kodak Portra 400 grade. "
            "Photorealistic fashion editorial. 9:16 vertical. "
            f"Negative: {NEGATIVE_UNIVERSAL}"
        ),
        "veo_motion_prompt": (
            "Animate the starting frame. Juan's left hand slowly pulls the zipper down 8cm "
            "in 3 seconds, then slowly zips it back up. The caramel suede fabric parts slightly "
            "revealing black tee underneath. Camera: perfectly locked, no movement. "
            "5 seconds."
        )
    },
    {
        "shot_number": 4,
        "name": "mirror_adjustment",
        "description": "Juan ajustando las solapas frente al espejo — shot de confianza",
        "duration_seconds": 5,
        "prompt": (
            f"{MASTER_IDENTITY} "
            "Medium shot (waist up) of Juan standing before the boutique mirror, both hands "
            "adjusting the structured lapels of the caramel faux suede jacket with deliberate "
            "masculine confidence. His gaze goes to his own reflection in the mirror — "
            "direct, assured, self-aware. Left tattoo sleeve visible on forearm as arm raises. "
            "Mirror reflects warm boutique interior behind him. "
            "Lighting: warm tungsten key, soft fill, slight rim light from behind. "
            "35mm lens, f/2.0. Editorial menswear campaign mood. Photorealistic. 9:16 vertical. "
            f"Negative: {NEGATIVE_UNIVERSAL}"
        ),
        "veo_motion_prompt": (
            "Animate the starting frame. Juan makes two precise lapel adjustments — "
            "first left lapel, then right — fingers pressing the suede fabric flat with authority. "
            "After adjusting, both hands drop naturally to sides. He holds his own gaze in the "
            "mirror for 2 seconds — no smile, just confidence. Camera: slow push-in 2%, "
            "barely perceptible. 5 seconds."
        )
    },
    {
        "shot_number": 5,
        "name": "walking_boutique",
        "description": "Juan caminando hacia cámara en la boutique — walking shot dinámico",
        "duration_seconds": 5,
        "prompt": (
            f"{MASTER_IDENTITY} "
            "Full body shot of Juan walking directly toward camera through the boutique hallway. "
            "He wears the caramel faux suede jacket fully zipped, black trousers, black Chelsea "
            "boots. His left arm swings naturally showing tattoo sleeve, right hand relaxed. "
            "The jacket moves with his stride — suede fabric catching warm ambient light. "
            "Boutique corridor: cream walls, clothing rails with garments on both sides, "
            "large storefront window at the far end backlit with soft daylight. "
            "Camera angle: low angle (hip level) looking up slightly — makes subject imposing. "
            "28mm lens, f/2.8, slight motion blur on background. "
            "Cinematic menswear editorial. Photorealistic. 9:16 vertical. "
            f"Negative: {NEGATIVE_UNIVERSAL}"
        ),
        "veo_motion_prompt": (
            "Juan walks at relaxed confident pace toward camera, covering 4 meters in 5 seconds. "
            "Camera: smooth tracking backward at same speed as subject approach (Steadicam style). "
            "Jacket suede fabric moves with stride — subtle shine variation as fabric catches light. "
            "Left arm swing reveals full tattoo at second 2. Natural foot falls on concrete floor. "
            "5 seconds."
        )
    },
    {
        "shot_number": 6,
        "name": "hero_product_cta",
        "description": "Product shot hero — chamarra sola + precio + CTA",
        "duration_seconds": 5,
        "prompt": (
            "Studio product photography of the caramel faux suede collared jacket hanging on "
            "a minimalist matte black mannequin torso, centered in frame against pure matte black "
            "background. The jacket is fully zipped, lapels perfectly shaped. "
            "Three-point studio lighting: warm key light from upper-right catching suede texture, "
            "cool fill from left, subtle rim light outlining the jacket silhouette. "
            "The caramel color glows warmly against the black background. "
            "Shot on Phase One IQ4, 80mm, f/8, studio strobe. "
            "Premium fashion product photography. Photorealistic. 9:16 vertical. "
            f"Negative: {NEGATIVE_UNIVERSAL}, no person, no hands"
        ),
        "veo_motion_prompt": (
            "Very slow 360° rotation of the mannequin — 30° turn over 5 seconds showing "
            "jacket front-to-three-quarter view. Camera: perfectly locked. "
            "Studio lights remain fixed, suede texture changes character as jacket rotates. "
            "5 seconds, 9:16, 1080p."
        )
    }
]


class PersonaImageAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str, character_pack_dir: str = "character_pack"):
        super().__init__(agent_id, AgentRole.PRODUCER, session_id)
        self.character_pack_dir = character_pack_dir
        self.output_dir = os.path.join("output", "frames")
        os.makedirs(self.output_dir, exist_ok=True)

    def process_task(self, task: Task) -> Any:
        if task.type != "generate_frames":
            raise ValueError(f"Unsupported task type: {task.type}")

        product_spec = task.payload.get("product_spec", {})
        shot_numbers = task.payload.get("shot_numbers", list(range(1, 7)))

        logger.info(f"[PersonaImageAgent] Generating {len(shot_numbers)} frames with Nano Banana 2")

        # Load character pack reference images
        reference_images = self._load_character_pack()

        frames = []
        for shot_def in SHOT_DEFINITIONS:
            if shot_def["shot_number"] not in shot_numbers:
                continue

            logger.info(f"[PersonaImageAgent] Generating shot {shot_def['shot_number']}: {shot_def['name']}")
            try:
                frame_path = self._generate_frame(shot_def, reference_images, product_spec)
                frames.append({
                    "shot_number": shot_def["shot_number"],
                    "name": shot_def["name"],
                    "description": shot_def["description"],
                    "frame_path": frame_path,
                    "duration_seconds": shot_def["duration_seconds"],
                    "veo_motion_prompt": shot_def["veo_motion_prompt"]
                })
                logger.info(f"[PersonaImageAgent] ✅ Shot {shot_def['shot_number']} saved: {frame_path}")
            except Exception as e:
                logger.error(f"[PersonaImageAgent] ❌ Shot {shot_def['shot_number']} failed: {e}")
                frames.append({
                    "shot_number": shot_def["shot_number"],
                    "name": shot_def["name"],
                    "frame_path": None,
                    "error": str(e),
                    "veo_motion_prompt": shot_def["veo_motion_prompt"]
                })

        return {
            "frames": frames,
            "total_shots": len(frames),
            "successful": sum(1 for f in frames if f.get("frame_path")),
            "product_spec": product_spec
        }

    def _load_character_pack(self) -> list:
        """Carga las fotos de referencia de Juan desde character_pack/."""
        pack_dir = Path(self.character_pack_dir)
        reference_images = []

        priority_files = [
            "juan_anchor.jpg",    # Retrato frontal hero
            "juan_anchor.png",
            "juan_tattoo.jpg",    # Close-up del tatuaje
            "juan_tattoo.png",
            "juan_fullbody.jpg",  # Full body
            "juan_fullbody.png",
            "juan_mirror.jpg",    # Mirror selfie
            "juan_mirror.png",
        ]

        # Load in priority order
        for filename in priority_files:
            filepath = pack_dir / filename
            if filepath.exists():
                with open(filepath, "rb") as f:
                    img_bytes = f.read()
                reference_images.append({
                    "data": base64.b64encode(img_bytes).decode(),
                    "mime_type": "image/jpeg" if filename.endswith(".jpg") else "image/png",
                    "filename": filename
                })
                logger.info(f"[PersonaImageAgent] Loaded reference: {filename}")

        # Fallback: load any image in the directory
        if not reference_images and pack_dir.exists():
            for filepath in sorted(pack_dir.iterdir())[:4]:
                if filepath.suffix.lower() in [".jpg", ".jpeg", ".png"]:
                    with open(filepath, "rb") as f:
                        img_bytes = f.read()
                    reference_images.append({
                        "data": base64.b64encode(img_bytes).decode(),
                        "mime_type": "image/jpeg",
                        "filename": filepath.name
                    })

        if not reference_images:
            logger.warning("[PersonaImageAgent] ⚠️ No character pack found — generating without reference images")

        return reference_images

    def _generate_frame(self, shot_def: dict, reference_images: list, product_spec: dict) -> str:
        """Genera un frame con Nano Banana 2."""
        from google import genai
        from google.genai import types

        client = GoogleAIApp.get_client()

        # Build contents list
        contents = []

        # Add reference images first (character pack)
        for ref in reference_images[:4]:  # Max 4 character reference images
            contents.append(
                types.Part.from_bytes(
                    data=base64.b64decode(ref["data"]),
                    mime_type=ref["mime_type"]
                )
            )

        # Add the prompt
        prompt = shot_def["prompt"]
        if product_spec:
            price_line = (
                f"\nProduct context: {product_spec.get('name_es', '')}, "
                f"precio ${product_spec.get('price_current', '')} MXN, "
                f"color {product_spec.get('colors', ['caramel'])[0]}."
            )
            prompt += price_line

        contents.append(types.Part.from_text(text=prompt))

        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
                image_config=types.ImageConfig(
                    aspect_ratio="9:16",
                    image_size="2K",
                )
            )
        )

        # Extract image from response
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                img_bytes = part.inline_data.data
                filename = f"shot_{shot_def['shot_number']:02d}_{shot_def['name']}_{self.session_id}.png"
                filepath = os.path.join(self.output_dir, filename)
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                return filepath

        raise ValueError(f"No image returned for shot {shot_def['shot_number']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    import time
    agent = PersonaImageAgent("persona_image_01", "dev_session_001")
    agent.start()
    print("PersonaImageAgent running...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
