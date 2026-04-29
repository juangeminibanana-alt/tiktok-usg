import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getDatabase, ref, onValue, onChildAdded, push, set } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-database.js";

const firebaseConfig = {
  apiKey: "AIzaSyCGQPDDpxJk9-H1e5nIl5LaKBPHCHP1ZTE",
  authDomain: "e-book-21589.firebaseapp.com",
  projectId: "e-book-21589",
  storageBucket: "e-book-21589.firebasestorage.app",
  messagingSenderId: "1026985150312",
  appId: "1:1026985150312:web:465bb5cd336f00a86438dd",
  databaseURL: "https://e-book-21589-default-rtdb.firebaseio.com"
};

const app = initializeApp(firebaseConfig);
const db  = getDatabase(app);

const sessionIdInput = document.getElementById('session-id');
const connectBtn     = document.getElementById('connect-btn');
const promptInput    = document.getElementById('prompt-input');
const generateBtn    = document.getElementById('generate-btn');
const logFeed        = document.getElementById('log-feed');
const taskList       = document.getElementById('task-list');
const gallery        = document.getElementById('gallery');
const outputPreview  = document.getElementById('output-preview');

let currentSessionId = sessionIdInput.value;

function addLog(message, type = 'system', sender = 'System') {
    const entry = document.createElement('div');
    entry.className = `log-item ${type}`;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    entry.innerHTML = `<strong>${sender}</strong> <span style="color:var(--text-secondary);font-size:0.7rem;margin-left:5px;">${time}</span><br>${message}`;
    logFeed.prepend(entry);
}

function updateAgentCard(role, state) {
    const cardId = `${role}-status`;
    const card   = document.getElementById(cardId);
    if (!card) return;
    card.className = `agent-card ${state.status}`;
    card.querySelector('.status-text').textContent =
        state.status.charAt(0).toUpperCase() + state.status.slice(1);
    card.querySelector('.current-task').textContent =
        state.current_task_id ? `Task: ${state.current_task_id.slice(-6)}` : 'Idle';
}

// Pipeline steps → task type mapping (v2)
const STEP_MAP = {
    'analyze_product':   'step-analyzing',
    'generate_frames':   'step-imaging',
    'generate_clips':    'step-video',
    'generate_voiceover':'step-audio',
    'assemble_video':    'step-editing',
};

function updatePipelineStep(type, status) {
    const stepId = STEP_MAP[type];
    if (!stepId) return;
    const el = document.getElementById(stepId);
    if (!el) return;
    if (status === 'in_progress') { el.classList.add('active'); el.classList.remove('completed'); }
    else if (status === 'completed') { el.classList.remove('active'); el.classList.add('completed'); }
}

function connectToSession(sessionId) {
    addLog(`Conectando a sesión: ${sessionId}…`);
    logFeed.innerHTML = '';
    taskList.innerHTML = '';
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active', 'completed'));
    gallery.style.display = 'none';

    onValue(ref(db, `sessions/${sessionId}/agents`), (snap) => {
        const agents = snap.val();
        if (agents) Object.values(agents).forEach(a => updateAgentCard(a.role, a));
    });

    onChildAdded(ref(db, `sessions/${sessionId}/messages`), (snap) => {
        const msg = snap.val();
        addLog(msg.msg_type, 'message', msg.sender);
    });

    onValue(ref(db, `sessions/${sessionId}/tasks`), (snap) => {
        const tasks = snap.val();
        taskList.innerHTML = '';
        if (!tasks) return;

        Object.entries(tasks).reverse().forEach(([id, t]) => {
            updatePipelineStep(t.type, t.status);

            const item = document.createElement('div');
            item.className = `log-item task ${t.status}`;
            item.innerHTML = `
                <div style="font-weight:700">${t.type.replace(/_/g,' ').toUpperCase()}</div>
                <div style="font-size:0.7rem;color:var(--text-secondary)">
                    → ${t.assigned_to} | ${t.status}
                </div>`;
            taskList.appendChild(item);

            if (t.type === 'assemble_video' && t.status === 'completed' && t.result) {
                gallery.style.display = 'block';
                outputPreview.innerHTML = `
                    <div style="padding:1rem;background:rgba(16,185,129,0.1);border-radius:12px;border:1px solid var(--status-idle)">
                        <p style="margin-bottom:0.5rem">🎬 Video listo!</p>
                        <code>${t.result.video_path || 'ver output/'}</code>
                        ${t.result.has_audio ? '<p style="margin-top:0.5rem;color:#10b981">✅ Con voz en off</p>' : ''}
                    </div>`;
            }
        });
    });
}

async function triggerWorkflow() {
    const url = promptInput.value.trim();
    if (!url) return;
    addLog("Enviando START_WORKFLOW…", "system");

    const messagesRef    = ref(db, `sessions/${currentSessionId}/messages`);
    const newMessageRef  = push(messagesRef);
    await set(newMessageRef, {
        message_id: `msg_${Math.random().toString(36).substr(2, 9)}`,
        sender:     "web_ui",
        receiver:   "orchestrator",
        msg_type:   "start_workflow",
        content:    { url, manual_data: {}, character_pack_dir: "character_pack" },
        timestamp:  new Date().toISOString()
    });
    promptInput.value = '';
    addLog("✅ Workflow iniciado.", "system");
}

connectBtn.addEventListener('click', () => {
    currentSessionId = sessionIdInput.value;
    connectToSession(currentSessionId);
});
generateBtn.addEventListener('click', triggerWorkflow);
promptInput.addEventListener('keypress', e => { if (e.key === 'Enter') triggerWorkflow(); });

connectToSession(currentSessionId);
addLog("Sistema online — pega la URL de TikTok Shop y presiona Generate.", "system");
