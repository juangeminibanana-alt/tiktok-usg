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
            self._report_state()
            time.sleep(30)  # Heartbeat every 30 seconds

    def _report_state(self):
        self.bus.update_agent_state(self.state)

    def _message_handler(self, message: Message):
        """Internal dispatcher for incoming messages."""
        # Only process messages intended for this agent or broadcast
        if message.receiver and message.receiver != self.agent_id and message.receiver != self.role.value:
            return

        logger.debug(f"Agent {self.agent_id} received message: {message.msg_type}")
        
        if message.msg_type == MessageType.TASK_ASSIGNMENT:
            task_data = message.content
            if isinstance(task_data, dict):
                task = Task(**task_data)
                self._handle_task(task)

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

    def generate_content(self, model_name: str, prompt: str, system_instruction: str = None) -> str:
        """Helper to generate content with built-in retry for 503 errors."""
        client = GoogleAIApp.get_client()
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={
                        "system_instruction": system_instruction
                    } if system_instruction else None
                )
                return response.text
            except Exception as e:
                # Check for 503 in the error message
                if "503" in str(e) and attempt < max_retries - 1:
                    logger.warning(f"Model {model_name} busy (503). Retrying in {retry_delay}s... (Attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                    continue
                
                logger.error(f"Generation error with model {model_name}: {e}")
                raise

    def get_model(self, model_name: str = "gemini-2.0-flash") -> str:
        """Returns the model string identifier."""
        if "flash" in model_name:
            return GoogleAIApp.get_gemini_2_0_flash()
        elif "pro" in model_name:
            return GoogleAIApp.get_gemini_2_5_pro()
        return model_name
