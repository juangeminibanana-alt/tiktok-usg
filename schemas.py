"""
schemas.py
──────────
Pydantic models for the Multi-Agent System.
Defines the structure for messages, tasks, and state management.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class AgentRole(str, Enum):
    PLANNER = "planner"
    SCRIPTWRITER = "scriptwriter"
    PRODUCER = "producer"  # Handles video/image gen
    REVIEWER = "reviewer"
    ORCHESTRATOR = "orchestrator"
    EDITOR = "editor"

class AgentStatus(str, Enum):
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"

class MessageType(str, Enum):
    TASK_ASSIGNMENT = "task_assignment"
    TASK_UPDATE = "task_update"
    TASK_COMPLETE = "task_complete"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    START_WORKFLOW = "start_workflow"

class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    task_id: str = Field(..., description="Unique ID for the task")
    type: str = Field(..., description="Type of task (e.g., 'write_script', 'generate_video')")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Task-specific data")
    assigned_to: Optional[AgentRole] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Any] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class Message(BaseModel):
    message_id: str = Field(..., description="Unique ID for the message")
    sender: str = Field(..., description="ID or Role of the sender")
    receiver: Optional[str] = Field(None, description="ID or Role of the receiver (None for broadcast)")
    msg_type: MessageType
    content: Any
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

class AgentState(BaseModel):
    agent_id: str
    role: AgentRole
    status: AgentStatus = AgentStatus.IDLE
    current_task_id: Optional[str] = None
    last_heartbeat: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SessionState(BaseModel):
    session_id: str
    tasks: Dict[str, Task] = Field(default_factory=dict)
    agents: Dict[str, AgentState] = Field(default_factory=dict)
    global_context: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
