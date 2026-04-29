"""
schemas.py — v2 UGC Fashion Pipeline
──────────────────────────────────────
Pydantic models para el pipeline de moda masculina TikTok Shop.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    ORCHESTRATOR    = "orchestrator"
    PRODUCT_ANALYZER = "product_analyzer"
    PERSONA_IMAGE   = "persona_image"
    VEO_GENERATOR   = "veo_generator"
    ELEVENLABS      = "elevenlabs"
    EDITOR          = "editor"
    # Legacy (mantenidos para compatibilidad con dashboard existente)
    PLANNER         = "planner"
    SCRIPTWRITER    = "scriptwriter"
    PRODUCER        = "producer"
    REVIEWER        = "reviewer"


class AgentStatus(str, Enum):
    IDLE    = "idle"
    BUSY    = "busy"
    ERROR   = "error"
    OFFLINE = "offline"


class MessageType(str, Enum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_UPDATE     = "task_update"
    TASK_COMPLETE   = "task_complete"
    ERROR           = "error"
    HEARTBEAT       = "heartbeat"
    START_WORKFLOW  = "start_workflow"


class TaskStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    FAILED      = "failed"


# ── Dominio: Producto ──────────────────────────────────────────────────────────

class SizeChart(BaseModel):
    chest_cm:    Optional[float] = None
    shoulder_cm: Optional[float] = None
    length_cm:   Optional[float] = None


class ProductSpec(BaseModel):
    product_id:         str
    name_es:            str
    name_en:            str
    price_current:      float
    price_original:     float
    discount_pct:       int
    currency:           str = "MXN"
    seller:             str
    rating:             float
    reviews_count:      int
    units_sold:         int
    colors:             List[str]
    sizes:              List[str]
    size_chart:         Dict[str, SizeChart] = Field(default_factory=dict)
    material:           str
    material_composition: Optional[str] = None
    season:             List[str]
    style:              str
    closure_type:       Optional[str] = None
    collar_type:        Optional[str] = None
    usps:               List[str]
    hero_image_url:     Optional[str] = None
    additional_images:  List[str] = Field(default_factory=list)
    tiktok_url:         str
    ugc_hooks:          List[str] = Field(default_factory=list)
    target_audience:    str
    price_anchor_script: str


# ── Dominio: Producción ────────────────────────────────────────────────────────

class ShotFrame(BaseModel):
    shot_number:      int
    name:             str
    description:      str
    frame_path:       Optional[str] = None
    duration_seconds: int = 5
    veo_motion_prompt: str
    voiceover_text:   str = ""
    caption:          str = ""
    error:            Optional[str] = None


class VideoClip(BaseModel):
    shot_number:      int
    name:             str = ""
    clip_path:        Optional[str] = None
    duration_seconds: int = 5
    voiceover_text:   str = ""
    error:            Optional[str] = None


class WordTimestamp(BaseModel):
    word:  str
    start: float
    end:   float


class VoiceoverResult(BaseModel):
    audio_path:       str
    duration_seconds: float
    word_timestamps:  List[WordTimestamp] = Field(default_factory=list)
    script:           str
    voice_id:         str


# ── Infraestructura ────────────────────────────────────────────────────────────

class Task(BaseModel):
    task_id:     str   = Field(..., description="Unique ID for the task")
    type:        str   = Field(..., description="Task type")
    payload:     Dict[str, Any] = Field(default_factory=dict)
    assigned_to: Optional[AgentRole] = None
    status:      TaskStatus = TaskStatus.PENDING
    result:      Optional[Any] = None
    created_at:  str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at:  str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class Message(BaseModel):
    message_id: str = Field(..., description="Unique message ID")
    sender:     str
    receiver:   Optional[str] = None
    msg_type:   MessageType
    content:    Any
    timestamp:  str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class AgentState(BaseModel):
    agent_id:        str
    role:            AgentRole
    status:          AgentStatus = AgentStatus.IDLE
    current_task_id: Optional[str] = None
    last_heartbeat:  str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata:        Dict[str, Any] = Field(default_factory=dict)


class SessionState(BaseModel):
    session_id:     str
    tasks:          Dict[str, Task]       = Field(default_factory=dict)
    agents:         Dict[str, AgentState] = Field(default_factory=dict)
    global_context: Dict[str, Any]        = Field(default_factory=dict)
    created_at:     str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at:     str = Field(default_factory=lambda: datetime.utcnow().isoformat())
