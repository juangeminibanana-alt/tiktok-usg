"""
simulate_workflow.py — v2 UGC Fashion Pipeline
────────────────────────────────────────────────
Dispara el pipeline completo con la chamarra de ante café de TikTok Shop.

Uso:
    uv run simulate_workflow.py
    uv run simulate_workflow.py --url https://www.tiktok.com/view/product/1732992473481512755
"""

import argparse
import logging
import time
import uuid

from orchestrator_agent     import OrchestratorAgent
from product_analyzer_agent import ProductAnalyzerAgent
from persona_image_agent    import PersonaImageAgent
from veo_generator_agent    import VeoGeneratorAgent
from elevenlabs_agent       import ElevenLabsAgent
from editor_agent           import EditorAgent
from state_bus              import SharedStateBus
from schemas                import MessageType

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-25s  %(levelname)-8s  %(message)s",
)
logger = logging.getLogger("Simulation")

# ── Payload por defecto: chamarra de ante café ────────────────────────────────
DEFAULT_PAYLOAD = {
    "url": "https://www.tiktok.com/view/product/1732992473481512755",
    "manual_data": {
        "name":           "Chaqueta de ante sintético con cuello y cierre",
        "price_current":  363.74,
        "price_original": 757.78,
        "discount_pct":   52,
        "colors":         ["caramel", "gray", "black", "olive green"],
        "sizes":          ["S", "M", "L", "XL", "XXL"],
        "material":       "Faux suede premium",
        "seller":         "Value Chic Clothes",
        "rating":         4.8,
        "reviews":        205,
        "sold":           2000,
    },
    "character_pack_dir": "character_pack",
    # "voice_id": "TU_ELEVENLABS_VOICE_ID",  # Descomentar cuando tengas la voz clonada
}


def run_simulation(payload: dict = None):
    if payload is None:
        payload = DEFAULT_PAYLOAD

    session_id = f"ugc_{uuid.uuid4().hex[:6]}"
    logger.info(f"Session: {session_id}")
    logger.info(f"Producto: {payload.get('manual_data', {}).get('name', 'desconocido')}")

    # Instanciar todos los agentes
    agents = [
        OrchestratorAgent    ("orchestrator_01",    session_id),
        ProductAnalyzerAgent ("product_analyzer_01", session_id),
        PersonaImageAgent    ("persona_image_01",    session_id),
        VeoGeneratorAgent    ("veo_generator_01",    session_id),
        ElevenLabsAgent      ("elevenlabs_01",       session_id),
        EditorAgent          ("editor_01",           session_id),
    ]

    for agent in agents:
        agent.start()

    logger.info("Agentes iniciados — esperando 3s para que Firebase conecte…")
    time.sleep(3)

    # Disparar el workflow
    bus     = SharedStateBus(session_id)
    trigger = bus.create_message(
        sender   = "user_proxy",
        receiver = "orchestrator",
        msg_type = MessageType.START_WORKFLOW,
        content  = payload,
    )
    bus.push_message(trigger)
    logger.info("✅ START_WORKFLOW enviado — pipeline corriendo.")
    logger.info("Monitorea en: dashboard/index.html | Ctrl-C para detener")

    try:
        while True:
            time.sleep(5)
            final = next(
                (a for a in agents if hasattr(a, "workflow_state")),
                None
            )
            if final and final.workflow_state.get("final_output"):
                output = final.workflow_state["final_output"]
                logger.info(f"🎬 VIDEO LISTO: {output.get('video_path')}")
                break
    except KeyboardInterrupt:
        pass
    finally:
        for agent in agents:
            agent.stop()
        logger.info("Agentes detenidos.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="URL de TikTok Shop del producto")
    args = parser.parse_args()

    payload = DEFAULT_PAYLOAD.copy()
    if args.url:
        payload["url"] = args.url

    run_simulation(payload)
