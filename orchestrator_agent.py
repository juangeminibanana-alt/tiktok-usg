"""
orchestrator_agent.py — v2 UGC Fashion Pipeline
─────────────────────────────────────────────────
Pipeline completo para videos UGC de moda masculina TikTok Shop:

  START_WORKFLOW
      │
      ▼
  analyze_product       ← ProductAnalyzerAgent
      │
      ▼
  generate_frames       ← PersonaImageAgent (Nano Banana 2)
      │
      ▼
  generate_clips        ← VeoGeneratorAgent (Veo 3.1 Lite)
      │
      ▼
  generate_voiceover    ← ElevenLabsAgent
      │
      ▼
  assemble_video        ← EditorAgent (MoviePy: clips + audio)
      │
      ▼
  ✅ DONE
"""

import logging
import threading
import uuid
from agent_base import BaseAgent
from schemas import AgentRole, Message, MessageType, Task, TaskStatus

logger = logging.getLogger(__name__)


class OrchestratorAgent(BaseAgent):
    def __init__(self, agent_id: str, session_id: str):
        super().__init__(agent_id, AgentRole.ORCHESTRATOR, session_id)
        self.workflow_state: dict = {}

    # ── Message dispatch ──────────────────────────────────────────────────────

    def _message_handler(self, message: Message):
        super()._message_handler(message)
        if message.msg_type == MessageType.START_WORKFLOW:
            threading.Thread(
                target=self._start_workflow,
                args=(message.content,),
                daemon=True,
                name="orchestrator-start-workflow",
            ).start()
        elif message.msg_type == MessageType.TASK_COMPLETE:
            threading.Thread(
                target=self._handle_task_completion,
                args=(message.content,),
                daemon=True,
                name="orchestrator-task-complete",
            ).start()

    # ── Entrada del workflow ──────────────────────────────────────────────────

    def _start_workflow(self, payload):
        """
        payload puede ser:
          - str  → URL de TikTok Shop
          - dict → {url, manual_data, character_pack_dir}
        """
        if isinstance(payload, str):
            payload = {"url": payload}

        logger.info(f"[Orchestrator] ▶ Workflow iniciado — {str(payload)[:80]}…")
        self.workflow_state["input"] = payload

        self._assign_task(
            task_type="analyze_product",
            payload={
                "url":          payload.get("url", ""),
                "manual_data":  payload.get("manual_data", {}),
                "screenshots":  payload.get("screenshots", []),
            },
            assigned_to=AgentRole.PRODUCT_ANALYZER,
        )

    # ── Router de tareas completadas ──────────────────────────────────────────

    def _handle_task_completion(self, completion_data: dict):
        task_id = completion_data.get("task_id")
        status  = completion_data.get("status")
        result  = completion_data.get("result")

        logger.info(f"[Orchestrator] Task {task_id} → {status}")

        if status != TaskStatus.COMPLETED:
            logger.error(f"[Orchestrator] ❌ Task {task_id} FALLÓ — pipeline detenido.")
            self.workflow_state["error"] = f"Task {task_id} failed"
            return

        task = self.bus.get_task(task_id)
        if not task:
            logger.warning(f"[Orchestrator] No se encontró task {task_id} en el bus.")
            return

        # ── Paso 1 completado: producto analizado ──────────────────────────
        if task.type == "analyze_product":
            product_spec = result
            self.workflow_state["product_spec"] = product_spec
            logger.info(f"[Orchestrator] Producto: {product_spec.get('name_es', '?')}")

            char_pack = self.workflow_state["input"].get(
                "character_pack_dir", "character_pack"
            )
            self._assign_task(
                task_type="generate_frames",
                payload={
                    "product_spec":       product_spec,
                    "character_pack_dir": char_pack,
                    "shot_numbers":       [1, 2, 3, 4, 5, 6],
                },
                assigned_to=AgentRole.PERSONA_IMAGE,
            )

        # ── Paso 2 completado: frames generados ───────────────────────────
        elif task.type == "generate_frames":
            frames_result = result
            self.workflow_state["frames"] = frames_result

            successful = frames_result.get("successful", 0)
            total      = frames_result.get("total_shots", 0)
            logger.info(f"[Orchestrator] Frames: {successful}/{total} exitosos")

            valid_frames = [
                f for f in frames_result.get("frames", [])
                if f.get("frame_path")
            ]
            if not valid_frames:
                logger.error("[Orchestrator] ❌ Sin frames válidos — pipeline detenido.")
                return

            self._assign_task(
                task_type="generate_clips",
                payload={"frames": valid_frames},
                assigned_to=AgentRole.VEO_GENERATOR,
            )

        # ── Paso 3 completado: clips de video generados ───────────────────
        elif task.type == "generate_clips":
            clips_result = result
            self.workflow_state["clips"] = clips_result

            successful = clips_result.get("successful", 0)
            logger.info(f"[Orchestrator] Clips Veo: {successful} generados")

            # Lanzar voiceover en paralelo con la lógica que ya tenemos
            product_spec = self.workflow_state.get("product_spec", {})
            self._assign_task(
                task_type="generate_voiceover",
                payload={
                    "script":                  self._build_voiceover_script(product_spec),
                    "voice_id":                self.workflow_state["input"].get("voice_id", ""),
                    "target_duration_seconds": 28,
                },
                assigned_to=AgentRole.ELEVENLABS,
            )

        # ── Paso 4 completado: voz en off generada ────────────────────────
        elif task.type == "generate_voiceover":
            vo_result = result
            self.workflow_state["voiceover"] = vo_result
            logger.info(f"[Orchestrator] VO generado: {vo_result.get('audio_path')}")

            clips_result = self.workflow_state.get("clips", {})
            valid_clips  = [
                c for c in clips_result.get("clips", [])
                if c.get("clip_path")
            ]

            self._assign_task(
                task_type="assemble_video",
                payload={
                    "clips":     valid_clips,
                    "voiceover": vo_result,
                    "product_spec": self.workflow_state.get("product_spec", {}),
                },
                assigned_to=AgentRole.EDITOR,
            )

        # ── Paso 5 completado: video final ensamblado ─────────────────────
        elif task.type == "assemble_video":
            self.workflow_state["final_output"] = result
            logger.info(
                f"[Orchestrator] ✅ PIPELINE COMPLETO — "
                f"Video: {result.get('video_path', 'n/a')}"
            )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _build_voiceover_script(self, product_spec: dict) -> str:
        """Construye el script de VO desde el ProductSpec."""
        hooks    = product_spec.get("ugc_hooks", ["Esta chamarra lo tiene todo"])
        hook     = hooks[0] if hooks else "Esta chamarra lo tiene todo"
        usps     = product_spec.get("usps", [])
        usp1     = usps[0] if len(usps) > 0 else "Calidad premium"
        usp2     = usps[1] if len(usps) > 1 else "Diseño único"
        anchor   = product_spec.get("price_anchor_script", "Gran descuento en TikTok Shop")

        return (
            f"[excited] {hook}. "
            f"{usp1}... [pauses] {usp2}. "
            f"[confident] {anchor}. "
            f"[excited] Toca la canastita amarilla."
        )

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
        logger.info(
            f"[Orchestrator] → '{task_type}' asignado a {assigned_to.value} "
            f"(task_id={task.task_id})"
        )
        return task

    def process_task(self, task: Task):
        return "Acknowledged"


if __name__ == "__main__":
    import time
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s"
    )
    session_id  = "dev_session_001"
    orchestrator = OrchestratorAgent("orchestrator_main", session_id)
    orchestrator.start()
    print(f"Orchestrator v2 corriendo — session: {session_id}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        orchestrator.stop()
