"""
start_agents.py — v2
─────────────────────
Arranca TODOS los agentes del pipeline UGC de moda.
Espera triggers desde el Dashboard o simulate_workflow.py.

Uso:
    uv run start_agents.py
    uv run start_agents.py --session mi_sesion_001
"""

import argparse
import logging
import os
import signal
import sys
import threading
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler

from orchestrator_agent     import OrchestratorAgent
from product_analyzer_agent import ProductAnalyzerAgent
from persona_image_agent    import PersonaImageAgent
from veo_generator_agent    import VeoGeneratorAgent
from elevenlabs_agent       import ElevenLabsAgent
from editor_agent           import EditorAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-25s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("AgentRunner")


def _serve_dashboard(port: int = 8080):
    """Serves the dashboard folder over HTTP so ES modules work in Chrome."""
    dashboard_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dashboard")

    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=dashboard_dir, **kwargs)

        def log_message(self, format, *args):  # silence request logs
            pass

    server = HTTPServer(("localhost", port), QuietHandler)
    logger.info(f"🌐 Dashboard disponible en http://localhost:{port}")
    server.serve_forever()



def start_all(session_id: str = "dev_session_001"):
    logger.info(f"🚀 Pipeline UGC iniciando — Session: {session_id}")

    # Serve dashboard via HTTP (ES modules don't work from file://)
    dashboard_thread = threading.Thread(target=_serve_dashboard, daemon=True)
    dashboard_thread.start()

    agents = [
        OrchestratorAgent    ("orchestrator_01",     session_id),
        ProductAnalyzerAgent ("product_analyzer_01", session_id),
        PersonaImageAgent    ("persona_image_01",    session_id),
        VeoGeneratorAgent    ("veo_generator_01",    session_id),
        ElevenLabsAgent      ("elevenlabs_01",       session_id),
        EditorAgent          ("editor_01",           session_id),
    ]

    for agent in agents:
        agent.start()

    logger.info("✅ Todos los agentes activos — esperando triggers del Dashboard…")
    logger.info("   Abre: dashboard/index.html")

    def _shutdown(sig, frame):
        logger.info("\nDeteniendo agentes…")
        for agent in agents:
            agent.stop()
        logger.info("Pipeline detenido.")
        sys.exit(0)

    signal.signal(signal.SIGINT,  _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    while True:
        time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline UGC de moda TikTok Shop")
    parser.add_argument("--session", default="dev_session_001", help="Session ID")
    args = parser.parse_args()
    start_all(args.session)
