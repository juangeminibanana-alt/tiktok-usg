"""
scriptwriter_agent.py
─────────────────────
Genera un guion estructurado en JSON con escenas y prompts visuales.
"""

import json
import logging
import re
from typing import Any
from agent_base import BaseAgent
from schemas import AgentRole, Task

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """
You are a professional TikTok scriptwriter and visual director.

Given a creative plan, generate a structured video script in VALID JSON format.
The JSON must have this exact structure:
{
  "title": "Video title",
  "duration_seconds": 30,
  "scenes": [
    {
      "scene_number": 1,
      "duration_seconds": 5,
      "visual_prompt": "Detailed image generation prompt in English, cinematic style, 9:16 vertical format",
      "voiceover": "Text spoken in this scene",
      "caption": "On-screen text or caption"
    }
  ]
}

Rules:
- Generate exactly 5-6 scenes for a 30-second video.
- Each visual_prompt must be detailed and descriptive for an image AI model.
- Keep voiceover short and punchy (TikTok style).
- ONLY return valid JSON, no markdown, no extra text.
"""

class ScriptwriterAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.SCRIPTWRITER, session_id)

    def process_task(self, task: Task) -> Any:
        if task.type != "write_script":
            raise ValueError(f"Unsupported task type: {task.type}")

        plan = task.payload.get("plan")
        if not plan:
            raise ValueError("No plan provided in task payload")

        logger.info("Writing structured JSON script based on plan.")

        raw = self.generate_content(
            model_name=self.get_model("flash"),
            prompt=f"Creative Plan:\n{plan}",
            system_instruction=SYSTEM_INSTRUCTION
        )

        # Strip markdown fences if present
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

        try:
            script_data = json.loads(cleaned)
            logger.info(f"Script generated: {len(script_data.get('scenes', []))} scenes.")
            return script_data
        except json.JSONDecodeError:
            logger.warning("Could not parse JSON — wrapping raw text as single scene.")
            return {
                "title": "Generated Video",
                "duration_seconds": 30,
                "scenes": [
                    {
                        "scene_number": 1,
                        "duration_seconds": 30,
                        "visual_prompt": plan[:500],
                        "voiceover": raw[:300],
                        "caption": "AI Generated"
                    }
                ]
            }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import time
    agent = ScriptwriterAgent("scriptwriter_01", "dev_session_001")
    agent.start()
    print("Scriptwriter Agent running...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        agent.stop()
