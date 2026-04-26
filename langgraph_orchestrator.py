import os
import asyncio
import logging
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import UGCState, Shot, ProductSpec
from product_analyzer_agent import ProductAnalyzerAgent
from persona_image_agent import PersonaImageAgent, SHOT_DEFINITIONS
from veo_generator_agent import VeoGeneratorAgent
from elevenlabs_agent import ElevenLabsAgent
from schemas import Task

logger = logging.getLogger(__name__)

from compositor_agent import CompositorAgent
from reviewer_agent_v2 import QAReviewerAgent

import uuid

# --- Nodos del Grafo ---

async def analyze_product_node(state: UGCState):
    try:
        agent = ProductAnalyzerAgent("analyzer_01", state["session_id"])
        task = Task(
            task_id=uuid.uuid4().hex,
            type="analyze_product", 
            payload={"url": state["tiktok_url"]}
        )
        product_spec_dict = agent.process_task(task)
        return {"product_spec": ProductSpec(**product_spec_dict), "status": "analyzed"}
    except Exception as e:
        logger.warning(f"[Orchestrator] Analyzer failed (Quota?): {e}. Using fallback spec.")
        # Fallback para la chamarra de ante café
        fallback_spec = {
            "product_id": "1732992473481512755",
            "name_es": "Chamarra de Ante Sintético Casual",
            "name_en": "Casual Faux Suede Jacket",
            "price_current": 363.0,
            "price_original": 757.0,
            "discount_pct": 52,
            "currency": "MXN",
            "seller": "TikTok Shop México",
            "usps": ["Ante sintético premium", "Corte casual", "Talla S-XXL"],
            "hero_image_url": "",
            "target_audience": "Hombres 25-45",
            "price_anchor_script": "De $757 a solo $363"
        }
        return {"product_spec": ProductSpec(**fallback_spec), "status": "analyzed_fallback"}

async def script_and_storyboard_node(state: UGCState):
    # En un futuro esto vendrá de un ScriptWriterAgent
    logger.info("[Orchestrator] Using Master Storyboard for Mexican UGC")
    shots = [Shot(**sd) for sd in SHOT_DEFINITIONS]
    return {"shots": shots, "status": "storyboarded"}

async def generate_assets_node(state: UGCState):
    session_id = state["session_id"]
    
    # 1. Nano Banana 2 Frames
    image_agent = PersonaImageAgent("persona_01", session_id)
    frame_task = Task(
        task_id=uuid.uuid4().hex,
        type="generate_frames", 
        payload={"product_spec": state["product_spec"].model_dump()}
    )
    frames_result = image_agent.process_task(frame_task)
    
    updated_shots = []
    for shot in state["shots"]:
        frame_info = next((f for f in frames_result["frames"] if f["shot_number"] == shot.shot_number), None)
        if frame_info:
            shot.frame_path = frame_info["frame_path"]
        updated_shots.append(shot)
    
    # 2. Veo 3.1 Lite Clips
    video_agent = VeoGeneratorAgent("veo_01", session_id)
    video_task = Task(
        task_id=uuid.uuid4().hex,
        type="generate_clips", 
        payload={"frames": [f for f in frames_result["frames"]]}
    )
    clips_result = video_agent.process_task(video_task)
    
    for shot in updated_shots:
        clip_info = next((c for c in clips_result["clips"] if c["shot_number"] == shot.shot_number), None)
        if clip_info:
            shot.clip_path = clip_info["clip_path"]
            
    return {"shots": updated_shots, "status": "assets_generated"}

async def generate_voiceover_node(state: UGCState):
    agent = ElevenLabsAgent("eleven_01", state["session_id"])
    task = Task(
        task_id=uuid.uuid4().hex,
        type="generate_voiceover", 
        payload={}
    )
    result = agent.process_task(task)
    return {"voiceover_path": result["audio_path"], "status": "audio_ready"}

async def composite_video_node(state: UGCState):
    agent = CompositorAgent("compositor_01", state["session_id"])
    task = Task(
        task_id=uuid.uuid4().hex,
        type="composite_ugc_video", 
        payload={
            "clips": [s.model_dump() for s in state["shots"]],
            "voiceover_path": state["voiceover_path"],
            "product_spec": state["product_spec"].model_dump()
        }
    )
    result = agent.process_task(task)
    return {"final_video_path": result["video_path"], "status": "video_ready"}

async def qa_review_node(state: UGCState):
    agent = QAReviewerAgent("qa_01", state["session_id"])
    task = Task(
        task_id=uuid.uuid4().hex,
        type="review_final_video", 
        payload={"video_path": state["final_video_path"]}
    )
    result = agent.process_task(task)
    return {
        "qa_score": result["total_score"], 
        "qa_feedback": result["feedback"],
        "status": "completed" if result["approved"] else "needs_retry"
    }

# --- Construcción del Grafo ---

workflow = StateGraph(UGCState)

# Añadir nodos
workflow.add_node("analyze_product", analyze_product_node)
workflow.add_node("script_storyboard", script_and_storyboard_node)
workflow.add_node("generate_assets", generate_assets_node)
workflow.add_node("generate_voiceover", generate_voiceover_node)
workflow.add_node("composite", composite_video_node)
workflow.add_node("qa_review", qa_review_node)

# Definir bordes
workflow.set_entry_point("analyze_product")
workflow.add_edge("analyze_product", "script_storyboard")

# Bifurcación: Generación de Visuales (Audio desactivado para esta prueba)
workflow.add_edge("script_storyboard", "generate_assets")
# workflow.add_edge("script_storyboard", "generate_voiceover") # Desactivado

# Sincronización para el Compositor
workflow.add_edge("generate_assets", "composite")
# workflow.add_edge("generate_voiceover", "composite") # Desactivado

workflow.add_edge("composite", "qa_review")
workflow.add_edge("qa_review", END)

# Compilar con persistencia en memoria
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

async def run_ugc_pipeline(tiktok_url: str, session_id: str):
    initial_state = {
        "session_id": session_id,
        "tiktok_url": tiktok_url,
        "product_spec": None,
        "script": None,
        "shots": [],
        "voiceover_path": None,
        "final_video_path": None,
        "qa_score": 0.0,
        "qa_feedback": None,
        "retries": 0,
        "status": "started"
    }
    
    config = {"configurable": {"thread_id": session_id}}
    
    async for event in app.astream(initial_state, config):
        for node, values in event.items():
            logger.info(f"Node '{node}' finished with status: {values.get('status')}")
    
    return app.get_state(config).values

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    url = "https://www.tiktok.com/view/product/1732992473481512755"
    asyncio.run(run_ugc_pipeline(url, "dev_session_2026_01"))
