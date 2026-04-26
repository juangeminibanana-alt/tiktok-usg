"""
start_agents.py
───────────────
Starts all agents in the background and waits for messages from the State Bus (e.g. from the Frontend).
"""

import logging
import time
import signal
import sys
from orchestrator_agent  import OrchestratorAgent
from planner_agent       import PlannerAgent
from scriptwriter_agent  import ScriptwriterAgent
from producer_agent      import ProducerAgent
from reviewer_agent      import ReviewerAgent
from editor_agent        import EditorAgent

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-20s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("AgentRunner")

def start_all(session_id="dev_session_001"):
    logger.info(f"🚀 Starting AI Pipeline Agents (Session: {session_id})")
    logger.info("Waiting for triggers from the Dashboard...")

    # 1 ── Instantiate agents
    agents = [
        OrchestratorAgent("orchestrator_01", session_id),
        PlannerAgent     ("planner_01",       session_id),
        ScriptwriterAgent("scriptwriter_01",  session_id),
        ProducerAgent    ("producer_01",       session_id),
        ReviewerAgent    ("reviewer_01",       session_id),
        EditorAgent      ("editor_01",         session_id),
    ]

    # 2 ── Start all agents
    for agent in agents:
        agent.start()

    def signal_handler(sig, frame):
        logger.info("\nStopping agents...")
        for agent in agents:
            agent.stop()
        logger.info("Done.")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # 3 ── Keep process alive
    while True:
        time.sleep(1)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", default="dev_session_001", help="Session ID to monitor")
    args = parser.parse_args()
    
    start_all(args.session)
