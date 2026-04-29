"""
agent_base.py
─────────────
Base class for all agents in the Multi-Agent System.
Handles communication with the SharedStateBus and interaction with Google AI.
"""

import abc
import logging
import threading
import time
from typing import Any, Optional

from state_bus import SharedStateBus
from schemas import AgentRole, AgentState, AgentStatus, Message, MessageType, Task, TaskStatus
from google_clients import GoogleAIApp

logger = logging.getLogger(__name__)

class BaseAgent(abc.ABC):
    def __init__(self, agent_id: str, role: AgentRole, session_id: str):
        self.agent_id = agent_id
        self.role = role
        self.session_id = session_id
        self.bus = SharedStateBus(session_id)
        self.state = AgentState(agent_id=agent_id, role=role)
        
        self._stop_event = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None

    def start(self):
        """Starts the agent's message listener and heartbeat."""
        logger.info(f"Starting agent {self.agent_id} ({self.role})")
        self.state.status = AgentStatus.IDLE
        self._report_state()
        
        # Start heartbeat thread
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        
        # Start listening for messages
        self.bus.listen_messages(self._message_handler)

    def stop(self):
        """Stops the agent."""
        logger.info(f"Stopping agent {self.agent_id}")
        self._stop_event.set()
        self.state.status = AgentStatus.OFFLINE
        self._report_state()

    def _heartbeat_loop(self):
        while not self._stop_event.is_set():
            try:
                self._report_state()
            except Exception as e:
                logger.warning(f"[{self.agent_id}] Heartbeat error (will retry in 30s): {type(e).__name__}")
            self._stop_event.wait(timeout=30)

    def _report_state(self):
        try:
            self.bus.update_agent_state(self.state)
        except Exception as e:
            logger.warning(f"[{self.agent_id}] State report failed: {type(e).__name__}: {e}")

    def _message_handler(self, message: Message):
        """Internal dispatcher — runs in a daemon thread to avoid blocking the Firebase listener."""
        # Only process messages intended for this agent or broadcast
        if message.receiver and message.receiver != self.agent_id and message.receiver != self.role.value:
            return

        logger.debug(f"Agent {self.agent_id} received message: {message.msg_type}")

        if message.msg_type == MessageType.TASK_ASSIGNMENT:
            task_data = message.content
            if isinstance(task_data, dict):
                task = Task(**task_data)
                # Dispatch to daemon thread — never block the Firebase listener
                threading.Thread(
                    target=self._handle_task,
                    args=(task,),
                    daemon=True,
                    name=f"{self.agent_id}-task-{task.task_id[:8]}",
                ).start()

    def _handle_task(self, task: Task):
        """Wraps task processing with state updates."""
        self.state.status = AgentStatus.BUSY
        self.state.current_task_id = task.task_id
        self._report_state()
        
        task.status = TaskStatus.IN_PROGRESS
        self.bus.update_task(task)
        
        try:
            result = self.process_task(task)
            task.status = TaskStatus.COMPLETED
            task.result = result
        except Exception as e:
            logger.error(f"Error processing task {task.task_id}: {e}")
            task.status = TaskStatus.FAILED
            task.result = str(e)
            
        self.bus.update_task(task)
        
        # Notify completion
        completion_msg = self.bus.create_message(
            sender=self.agent_id,
            msg_type=MessageType.TASK_COMPLETE,
            content={"task_id": task.task_id, "status": task.status, "result": task.result}
        )
        self.bus.push_message(completion_msg)
        
        self.state.status = AgentStatus.IDLE
        self.state.current_task_id = None
        self._report_state()

    @abc.abstractmethod
    def process_task(self, task: Task) -> Any:
        """
        Implementation of the agent's logic.
        Must be overridden by subclasses.
        """
        pass

    def generate_content(self, prompt: str, model_name: str = None, model: str = None, system_instruction: str = None, is_json: bool = False) -> Any:
        """Helper to generate content with built-in retry for 503 errors."""
        client = GoogleAIApp.get_client()
        
        # Resolve model name
        target_model = model or model_name or GoogleAIApp.get_gemini_flash()
        
        config = {}
        if system_instruction:
            config["system_instruction"] = system_instruction
        if is_json:
            config["response_mime_type"] = "application/json"

        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=target_model,
                    contents=prompt,
                    config=config if config else None
                )
                
                text = response.text
                if is_json:
                    import json
                    # Clean markdown if present
                    if text.startswith("```json"):
                        text = text.replace("```json", "").replace("```", "").strip()
                    try:
                        return json.loads(text)
                    except Exception as e:
                        logger.error(f"Failed to parse JSON response: {text}")
                        raise
                return text
            except Exception as e:
                # Check for 503 in the error message
                if "503" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Model {target_model} busy (503). Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                
                logger.error(f"Generation error with model {target_model}: {e}")
                raise

    def get_model(self, model_name: str = "gemini-2.0-flash") -> str:
        """Returns the model string identifier."""
        if "flash" in model_name:
            return GoogleAIApp.get_gemini_2_0_flash()
        elif "pro" in model_name:
            return GoogleAIApp.get_gemini_2_5_pro()
        return model_name
