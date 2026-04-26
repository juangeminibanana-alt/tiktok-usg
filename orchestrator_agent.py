"""
orchestrator_agent.py
─────────────────────
Coordinates the full multi-agent workflow:
  START_WORKFLOW → Planner → (Reviewer) → Scriptwriter → (Reviewer) → Producer

Listens for TASK_COMPLETE messages and advances the pipeline accordingly.
"""

import logging
import uuid
from agent_base import BaseAgent
from schemas import AgentRole, Message, MessageType, Task, TaskStatus

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.ORCHESTRATOR, session_id)
        # Tracks the sequence state per session
        self.workflow_state: dict = {}

    # ── Message dispatch ──────────────────────────────────────────────────────

    def _message_handler(self, message: Message):
        """Extended handler — intercepts workflow control messages."""
        super()._message_handler(message)

        if message.msg_type == MessageType.START_WORKFLOW:
            self._start_workflow(message.content)

        elif message.msg_type == MessageType.TASK_COMPLETE:
            self._handle_task_completion(message.content)

    # ── Workflow entry point ──────────────────────────────────────────────────

    def _start_workflow(self, initial_prompt: str):
        logger.info(f"[Orchestrator] Workflow started. Prompt: {initial_prompt[:80]}…")
        self.workflow_state["initial_prompt"] = initial_prompt

        # Step 1 → Planner
        self._assign_task(
            task_type="create_plan",
            payload={"prompt": initial_prompt},
            assigned_to=AgentRole.PLANNER,
        )

    # ── Task completion router ────────────────────────────────────────────────

    def _handle_task_completion(self, completion_data: dict):
        task_id = completion_data.get("task_id")
        status   = completion_data.get("status")
        result   = completion_data.get("result")

        logger.info(f"[Orchestrator] Task {task_id} → {status}")

        if status != TaskStatus.COMPLETED:
            logger.error(f"[Orchestrator] Task {task_id} FAILED — halting workflow.")
            return

        task = self.bus.get_task(task_id)
        if not task:
            logger.warning(f"[Orchestrator] Could not retrieve task {task_id} from bus.")
            return

        # Advance pipeline based on what just finished
        if task.type == "create_plan":
            # Plan ready → store it and review it before writing the script
            self.workflow_state["plan"] = result
            self._assign_task(
                task_type="review_plan",
                payload={"plan": result},
                assigned_to=AgentRole.REVIEWER,
            )

        elif task.type == "review_plan":
            review = result if isinstance(result, dict) else {}
            if review.get("approved") and review.get("score", 0) >= 6:
                logger.info("[Orchestrator] Plan approved — moving to scriptwriting.")
                self._assign_task(
                    task_type="write_script",
                    payload={"plan": self.workflow_state.get("plan", "")},
                    assigned_to=AgentRole.SCRIPTWRITER,
                )
            else:
                logger.warning(
                    f"[Orchestrator] Plan not approved (score {review.get('score')}). "
                    "Workflow paused — manual intervention needed."
                )

        elif task.type == "write_script":
            # Store the structured script (dict or str), then review it
            self.workflow_state["script"] = result
            # For review, send a readable version
            review_content = result if isinstance(result, str) else str(result)
            self._assign_task(
                task_type="review_script",
                payload={"script": review_content},
                assigned_to=AgentRole.REVIEWER,
            )

        elif task.type == "review_script":
            review = result if isinstance(result, dict) else {}
            if review.get("approved") and review.get("score", 0) >= 7:
                logger.info("[Orchestrator] Script approved — handing off to Producer.")
                # Pass the structured script dict to producer
                self._assign_task(
                    task_type="generate_video",
                    payload={"script": self.workflow_state.get("script", {})},
                    assigned_to=AgentRole.PRODUCER,
                )
            else:
                logger.warning(
                    f"[Orchestrator] Script not approved (score {review.get('score')}). "
                    "Needs revision."
                )

        elif task.type in ("generate_video", "generate_image"):
            logger.info(f"[Orchestrator] Asset ready. Handing off to Editor.")
            self._assign_task(
                task_type="assemble_video",
                payload={
                    "script": self.workflow_state.get("script", ""),
                    "assets": [result]
                },
                assigned_to=AgentRole.EDITOR
            )

        elif task.type == "assemble_video":
            logger.info(f"[Orchestrator] ✅ FINAL EXPORT READY! File: {result.get('video_path')}")
            self.workflow_state["final_output"] = result

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assign_task(self, task_type: str, payload: dict, assigned_to: AgentRole) -> Task:
        task = Task(
            task_id=f"task_{uuid.uuid4().hex[:8]}",
            type=task_type,
            payload=payload,
            assigned_to=assigned_to,
        )
        self.bus.update_task(task)

        msg = self.bus.create_message(
            sender=self.agent_id,
            receiver=assigned_to.value,
            msg_type=MessageType.TASK_ASSIGNMENT,
            content=task.model_dump(),
        )
        self.bus.push_message(msg)
        logger.info(f"[Orchestrator] Assigned '{task_type}' → {assigned_to.value} (task_id={task.task_id})")
        return task

    def process_task(self, task: Task):
        """Orchestrator handles no custom tasks directly."""
        return "Acknowledged"


# ── Standalone entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    import time
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    session_id = "dev_session_001"
    orchestrator = OrchestratorAgent("orchestrator_main", session_id)
    orchestrator.start()

    print(f"Orchestrator running — session: {session_id}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        orchestrator.stop()
