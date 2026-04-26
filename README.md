# TikTok AI Video Pipeline — Multi-Agent System

Automated TikTok video generation using a multi-agent architecture powered by Google AI (Gemini + Veo) and Firebase Realtime Database as a shared state bus.

## Architecture

```
User Prompt
    │
    ▼
┌─────────────────┐
│  Orchestrator   │  ← Coordinates the full pipeline
└────────┬────────┘
         │ delegates
    ┌────▼───────────────────────────────────────┐
    │                Pipeline                    │
    │  Planner → Reviewer → Scriptwriter         │
    │       → Reviewer → Producer                │
    └────────────────────────────────────────────┘
         │ shared state
    ┌────▼────────────────┐
    │  Firebase RTDB      │  ← /sessions/{id}/{agents,tasks,messages}
    └─────────────────────┘
```

### Agent Roles

| Agent | File | Responsibility |
|---|---|---|
| Orchestrator | `orchestrator_agent.py` | Pipeline coordination and task delegation |
| Planner | `planner_agent.py` | Converts prompt → structured video plan |
| Scriptwriter | `scriptwriter_agent.py` | Converts plan → scene-by-scene script |
| Reviewer | `reviewer_agent.py` | Quality & policy review with JSON scoring |
| Producer | `producer_agent.py` | Image/video generation via Veo / Gemini |

### Infrastructure

| File | Purpose |
|---|---|
| `firebase_config.py` | Firebase Admin SDK initialization |
| `state_bus.py` | Shared State Bus (push/listen/update) |
| `agent_base.py` | `BaseAgent` abstract class |
| `schemas.py` | Pydantic models (Message, Task, AgentState…) |
| `google_clients.py` | Factory for Gemini + Veo model instances |

## Setup

### 1. Install dependencies

```bash
# With uv (recommended)
uv sync

# Or with pip
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your keys
```

Required variables:

| Variable | Description |
|---|---|
| `GOOGLE_API_KEY` | Google AI Studio API key |
| `FIREBASE_DATABASE_URL` | Your Firebase Realtime DB URL |
| `FIREBASE_SA_KEY` | Path to service account JSON (default: `serviceAccountKey.json`) |
| `GOOGLE_CLOUD_PROJECT` | GCP project ID (needed for Vertex AI / Veo) |

### 3. Add your Firebase service account key

Download `serviceAccountKey.json` from the Firebase Console and place it in the project root.

> ⚠️ **Never commit this file.** It is already in `.gitignore`.

## Running

### Test Firebase connectivity

```bash
uv run test_connection.py
```

### Run the full simulation (all 5 agents in one process)

```bash
uv run simulate_workflow.py
```

### Run agents individually (production mode — separate processes/containers)

```bash
uv run orchestrator_agent.py &
uv run planner_agent.py &
uv run scriptwriter_agent.py &
uv run reviewer_agent.py &
uv run producer_agent.py &
```

## Monitoring Dashboard

We have included a real-time web dashboard to monitor the agents.

### How to open
1. Open `dashboard/index.html` in any modern web browser.
2. Or run a local server:
   ```bash
   python -m http.server 8000 --directory dashboard
   ```
3. Visit `http://localhost:8000`.

The dashboard connects directly to your Firebase database and shows:
- **Agent Status**: Real-time heartbeats and current tasks.
- **Message Log**: Live feed of the State Bus.
- **Task List**: History and status of all tasks in the session.
  ├── agents/
  │   ├── orchestrator_01/   ← AgentState
  │   ├── planner_01/
  │   └── …
  ├── tasks/
  │   ├── {task_id}/         ← Task
  │   └── …
  └── messages/
      ├── {push_id}/         ← Message
      └── …
```
