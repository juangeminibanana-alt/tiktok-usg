"""
state_bus.py
────────────
Shared State Bus implementation using Firebase Realtime Database.
Handles real-time communication and state synchronization between agents.
"""

import json
import logging
import uuid
from typing import Callable, Optional, Dict, Any
from datetime import datetime

from firebase_config import init_firebase, get_db_ref
from schemas import Message, Task, AgentState, SessionState, MessageType

logger = logging.getLogger(__name__)

class SharedStateBus:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.base_path = f"/sessions/{session_id}"
        init_firebase()
        self.db_ref = get_db_ref(self.base_path)
        
        # Ensure session exists
        if not self.db_ref.get():
            self._initialize_session()

    def _initialize_session(self):
        logger.info(f"Initializing new session: {self.session_id}")
        initial_state = SessionState(session_id=self.session_id)
        self.db_ref.set(initial_state.model_dump())

    def push_message(self, message: Message):
        """Pushes a message to the session's message queue."""
        msg_ref = self.db_ref.child("messages").push()
        msg_data = message.model_dump()
        msg_ref.set(msg_data)
        logger.debug(f"Pushed message {message.message_id} of type {message.msg_type}")

    @staticmethod
    def _normalize_message(data: dict) -> dict:
        """Normalize message data from any source (UI, legacy, backend)."""
        normalized = dict(data)
        # Ensure message_id exists
        if "message_id" not in normalized:
            normalized["message_id"] = str(uuid.uuid4())
        # Normalize msg_type to lowercase
        if "msg_type" in normalized:
            normalized["msg_type"] = str(normalized["msg_type"]).lower()
        return normalized

    def listen_messages(self, callback: Callable[[Message], None]):
        """
        Sets up a listener for new messages in the session.
        Only processes NEW messages — historical messages are skipped to prevent loops.
        """
        initialized = {"done": False}

        def _listener(event):
            if event.data and isinstance(event.data, dict):
                try:
                    if event.path == "/":
                        # This is the initial data dump — mark as seen and SKIP.
                        # We never want to replay historical workflow triggers.
                        initialized["done"] = True
                        logger.debug(f"Skipping {len(event.data)} historical messages on startup.")
                        return
                    else:
                        # This is a genuinely new message pushed after we started.
                        if not initialized["done"]:
                            logger.debug("Skipping early message before init.")
                            return
                        try:
                            normalized = self._normalize_message(event.data)
                            msg = Message(**normalized)
                            callback(msg)
                        except Exception as e:
                            logger.debug(f"Skipping unrecognized message: {e}")
                except Exception as e:
                    logger.debug(f"Listener error: {e}")

        self.db_ref.child("messages").listen(_listener)

    def update_task(self, task: Task):
        """Updates a task in the shared state."""
        task.updated_at = datetime.utcnow().isoformat()
        self.db_ref.child("tasks").child(task.task_id).set(task.model_dump())
        logger.info(f"Task {task.task_id} updated to {task.status}")

    def update_agent_state(self, agent_state: AgentState):
        """Updates an agent's state/heartbeat."""
        agent_state.last_heartbeat = datetime.utcnow().isoformat()
        self.db_ref.child("agents").child(agent_state.agent_id).set(agent_state.model_dump())

    def get_task(self, task_id: str) -> Optional[Task]:
        """Retrieves a task by ID."""
        data = self.db_ref.child("tasks").child(task_id).get()
        if data:
            return Task(**data)
        return None

    @staticmethod
    def create_message(sender: str, msg_type: MessageType, content: Any, receiver: str = None) -> Message:
        return Message(
            message_id=str(uuid.uuid4()),
            sender=sender,
            receiver=receiver,
            msg_type=msg_type,
            content=content
        )
