from typing import Annotated, List, Optional, Dict, Any
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class ProductSpec(BaseModel):
    product_id: str
    name_es: str
    name_en: str
    price_current: float
    price_original: float
    discount_pct: int
    currency: str
    seller: str
    usps: List[str]
    hero_image_url: str
    target_audience: str
    price_anchor_script: str

class Shot(BaseModel):
    shot_number: int
    name: str
    description: str
    frame_path: Optional[str] = None
    clip_path: Optional[str] = None
    duration_seconds: int = 5
    veo_motion_prompt: str
    voiceover_text: Optional[str] = None

class UGCState(TypedDict):
    # Input
    session_id: str
    tiktok_url: str
    
    # Artifacts
    product_spec: Optional[ProductSpec]
    script: Optional[Dict[str, str]]
    shots: List[Shot]
    voiceover_path: Optional[str]
    final_video_path: Optional[str]
    
    # Metadata & Quality
    qa_score: float
    qa_feedback: Optional[str]
    retries: int
    status: str
