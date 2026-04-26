"""
planner_agent.py
────────────────
Analyzes the user's initial prompt and generates a structured creative plan.
"""

import logging
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task

logger = logging.getLogger(__name__)

class PlannerAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.PLANNER, session_id)

    def process_task(self, task: Task) -> Any:
        if task.type != "create_plan":
            raise ValueError(f"Unsupported task type: {task.type}")

        prompt = task.payload.get("prompt")
        if not prompt:
            raise ValueError("No prompt provided in task payload")

        logger.info(f"Generating plan for: {prompt}")
        
        system_instruction = (
            "You are an expert TikTok content strategist. "
            "Your goal is to take a user prompt and create a high-level video plan. "
            "The plan should include: 1. Target Audience, 2. Core Hook, 3. Visual Style, 4. Scene Breakdown (brief)."
        )

        try:
            plan = self.generate_content(
                model_name=self.get_model("flash"),
                prompt=f"User Prompt: {prompt}",
                system_instruction=system_instruction
            )
            logger.info("Plan generated successfully.")
            return plan
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            raise

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    session_id = "dev_session_001"
    agent = PlannerAgent("planner_01", session_id)
    agent.start()
    
    print(f"Planner Agent running for session: {session_id}")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
