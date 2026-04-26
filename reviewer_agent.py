"""
reviewer_agent.py
─────────────────
Reviews scripts and creative plans for quality, coherence, and policy compliance.
Provides structured feedback or approval back to the Orchestrator.
"""

import logging
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task

logger = logging.getLogger(__name__)

REVIEW_PROMPT = """
You are a senior content reviewer for a TikTok automation pipeline.
Your job is to critically evaluate a script or plan according to these criteria:

1. **Clarity**: Is the content easy to understand for a general audience?
2. **Engagement**: Does it have a strong hook in the first 3 seconds?
3. **Policy Compliance**: Does it violate any TikTok community guidelines? (violence, misinformation, explicit content)
4. **Pacing**: Is the scene breakdown appropriate for a short-form video?
5. **Overall Score**: Provide a score from 1-10.

Respond in this exact JSON format:
{
  "approved": true/false,
  "score": 0-10,
  "feedback": "Your detailed feedback here",
  "suggestions": ["suggestion 1", "suggestion 2"]
}
"""

class ReviewerAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.REVIEWER, session_id)

    def process_task(self, task: Task) -> Any:
        if task.type == "review_script":
            return self._review_content(task.payload.get("script", ""), "script")
        elif task.type == "review_plan":
            return self._review_content(task.payload.get("plan", ""), "plan")
        else:
            raise ValueError(f"Unsupported task type: {task.type}")

    def _review_content(self, content: str, content_type: str) -> dict:
        logger.info(f"Reviewing {content_type}...")

        try:
            raw = self.generate_content(
                model_name=self.get_model("flash"),
                prompt=f"--- {content_type.upper()} TO REVIEW ---\n{content}",
                system_instruction=REVIEW_PROMPT
            ).strip()
            
            # Try to parse as JSON
            import json
            # Strip potential markdown code block
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            
            review = json.loads(raw)
            logger.info(f"Review complete. Approved: {review.get('approved')}, Score: {review.get('score')}")
            return review

        except Exception as e:
            logger.error(f"Review failed: {e}")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    session_id = "dev_session_001"
    agent = ReviewerAgent("reviewer_01", session_id)
    agent.start()

    print(f"Reviewer Agent running for session: {session_id}")
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
