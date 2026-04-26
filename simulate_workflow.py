"""
simulate_workflow.py
─────────────────────
Runs all four agents in a single process (each in its own daemon thread)
and fires a START_WORKFLOW trigger to exercise the full pipeline.

Usage:
    uv run simulate_workflow.py
    # or
    python simulate_workflow.py
"""

import logging
import time
import uuid

from orchestrator_agent  import OrchestratorAgent
from planner_agent       import PlannerAgent
from scriptwriter_agent  import ScriptwriterAgent
from producer_agent      import ProducerAgent
from reviewer_agent      import ReviewerAgent
from editor_agent        import EditorAgent
from state_bus           import SharedStateBus
from schemas             import MessageType

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-20s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("Simulation")

# ── Sample prompt ─────────────────────────────────────────────────────────────
DEMO_PROMPT = (
    "Create a 30-second TikTok about the history of artificial intelligence, "
    "focusing on the shift from symbolic AI to neural networks. "
    "Use a dark, futuristic aesthetic with epic background music."
)

# ── Entry point ───────────────────────────────────────────────────────────────
def run_simulation():
    session_id = f"sim_{uuid.uuid4().hex[:6]}"
    logger.info(f"Session: {session_id}")
    logger.info(f"Prompt : {DEMO_PROMPT[:80]}…")

    # 1 ── Instantiate agents
    agents = [
        OrchestratorAgent("orchestrator_01", session_id),
        PlannerAgent     ("planner_01",       session_id),
        ScriptwriterAgent("scriptwriter_01",  session_id),
        ProducerAgent    ("producer_01",       session_id),
        ReviewerAgent    ("reviewer_01",       session_id),
        EditorAgent      ("editor_01",         session_id),
    ]

    # 2 ── Start all agents (each registers a Firebase listener in a daemon thread)
    for agent in agents:
        agent.start()

    logger.info("All agents started — waiting 2 s for Firebase listeners to attach…")
    time.sleep(2)

    # 3 ── Fire the trigger
    bus = SharedStateBus(session_id)
    trigger = bus.create_message(
        sender="user_proxy",
        receiver="orchestrator",
        msg_type=MessageType.START_WORKFLOW,
        content=DEMO_PROMPT,
    )
    bus.push_message(trigger)
    logger.info("START_WORKFLOW message sent — pipeline is running.")

    # 4 ── Keep process alive; Ctrl-C to stop
    try:
        logger.info("Monitoring (Ctrl-C to stop)…")
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Stopping agents…")
        for agent in agents:
            agent.stop()
        logger.info("Done.")


if __name__ == "__main__":
    run_simulation()
