import os
import asyncio
import logging
import uuid
from typing import Dict, Any, List
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from state import UGCState, Shot, ProductSpec
from product_analyzer_agent import ProductAnalyzerAgent
from persona_image_agent import PersonaImageAgent, SHOT_DEFINITIONS
from veo_generator_agent import VeoGeneratorAgent
from script_writer_agent import ScriptWriterAgent
from compositor_agent import CompositorAgent
from reviewer_agent_v2 import QAReviewerAgent
from schemas import Task

logger = logging.getLogger(__name__)

async def analyze_product_node(state: UGCState):
    try:
        agent = ProductAnalyzerAgent("analyzer_01", state["session_id"])
        task = Task(task_id=uuid.uuid4().hex, type="analyze_product", payload={"url": state["tiktok_url"]})
        res = agent.process_task(task)
        return {"product_spec": ProductSpec(**res), "status": "analyzed"}
    except Exception as e:
        logger.warning(f"Fallback: {e}")
        fallback = {"product_id": "1", "name_es": "Chamarra de Ante", "price_current": 363.0, "discount_pct": 52}
        return {"product_spec": ProductSpec(**fallback), "status": "analyzed_fallback"}

async def script_and_storyboard_node(state: UGCState):
    agent = ScriptWriterAgent("script_01", state["session_id"])
    task = Task(task_id=uuid.uuid4().hex, type="write_script", payload={"product_spec": state["product_spec"].model_dump()})
    script_data = agent.process_task(task)
    shots = [Shot(**sd) for sd in SHOT_DEFINITIONS]
    if "text_overlays" in script_data:
        for i, text in enumerate(script_data["text_overlays"][:6]):
            shots[i].name = text
    return {"script": script_data, "shots": shots, "status": "storyboarded"}

async def generate_assets_node(state: UGCState):
    img_agent = PersonaImageAgent("persona_01", state["session_id"])
    task = Task(task_id=uuid.uuid4().hex, type="generate_frames", payload={"product_spec": state["product_spec"].model_dump()})
    res = img_agent.process_task(task)
    updated_shots = []
    for shot in state["shots"]:
        info = next((f for f in res["frames"] if f["shot_number"] == shot.shot_number), None)
        if info: shot.frame_path = info["frame_path"]
        updated_shots.append(shot)
    vid_agent = VeoGeneratorAgent("veo_01", state["session_id"])
    v_task = Task(task_id=uuid.uuid4().hex, type="generate_clips", payload={"frames": res["frames"]})
    v_res = vid_agent.process_task(v_task)
    for shot in updated_shots:
        c_info = next((c for c in v_res["clips"] if c["shot_number"] == shot.shot_number), None)
        if c_info: shot.clip_path = c_info["clip_path"]
    return {"shots": updated_shots, "status": "assets_generated"}

async def composite_video_node(state: UGCState):
    agent = CompositorAgent("compositor_01", state["session_id"])
    task = Task(task_id=uuid.uuid4().hex, type="composite_ugc_video", payload={
        "clips": [s.model_dump() for s in state["shots"]],
        "product_spec": state["product_spec"].model_dump()
    })
    res = agent.process_task(task)
    return {"final_video_path": res["video_path"], "status": "video_ready"}

async def qa_review_node(state: UGCState):
    agent = QAReviewerAgent("qa_01", state["session_id"])
    task = Task(task_id=uuid.uuid4().hex, type="review_final_video", payload={"video_path": state["final_video_path"]})
    res = agent.process_task(task)
    return {"qa_score": res["total_score"], "status": "completed" if res["approved"] else "needs_retry"}

workflow = StateGraph(UGCState)
workflow.add_node("analyze_product", analyze_product_node)
workflow.add_node("script_storyboard", script_and_storyboard_node)
workflow.add_node("generate_assets", generate_assets_node)
workflow.add_node("composite", composite_video_node)
workflow.add_node("qa_review", qa_review_node)
workflow.set_entry_point("analyze_product")
workflow.add_edge("analyze_product", "script_storyboard")
workflow.add_edge("script_storyboard", "generate_assets")
workflow.add_edge("generate_assets", "composite")
workflow.add_edge("composite", "qa_review")
workflow.add_edge("qa_review", END)

app = workflow.compile(checkpointer=MemorySaver())

async def run_ugc_pipeline(url: str, session_id: str):
    init = {"session_id": session_id, "tiktok_url": url, "shots": [], "status": "started"}
    config = {"configurable": {"thread_id": session_id}}
    async for event in app.astream(init, config):
        for node, values in event.items():
            logger.info(f"Node '{node}' finished: {values.get('status')}")
    return app.get_state(config).values

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_ugc_pipeline("https://www.tiktok.com/view/product/1732992473481512755", "dev_session_2026_01"))
