import { initializeApp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-app.js";
import { getDatabase, ref, onValue, onChildAdded, push, set, serverTimestamp } from "https://www.gstatic.com/firebasejs/10.8.0/firebase-database.js";

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
const db = getDatabase(app);

// DOM Elements
const sessionIdInput = document.getElementById('session-id');
const connectBtn = document.getElementById('connect-btn');
const promptInput = document.getElementById('prompt-input');
const generateBtn = document.getElementById('generate-btn');
const logFeed = document.getElementById('log-feed');
const taskList = document.getElementById('task-list');
const gallery = document.getElementById('gallery');
const outputPreview = document.getElementById('output-preview');

let currentSessionId = sessionIdInput.value;
let activeListeners = [];

function addLog(message, type = 'system', sender = 'System') {
    const entry = document.createElement('div');
    entry.className = `log-item ${type}`;
    const time = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    entry.innerHTML = `<strong>${sender}</strong> <span style="color:var(--text-secondary); font-size: 0.7rem; margin-left:5px;">${time}</span><br>${message}`;
    logFeed.prepend(entry);
}

function updateAgentCard(role, state) {
    const cardId = `${role}-status`;
    const card = document.getElementById(cardId);
    if (!card) return;

    const statusText = card.querySelector('.status-text');
    const taskEl = card.querySelector('.current-task');

    card.className = `agent-card ${state.status}`;
    statusText.textContent = state.status.charAt(0).toUpperCase() + state.status.slice(1);
    taskEl.textContent = state.current_task_id ? `Active Task: ${state.current_task_id.slice(-6)}` : 'Idle';
}

function updatePipelineStep(taskId, type, status) {
    const mapping = {
        'create_plan': 'step-planning',
        'review_plan': 'step-planning',
        'write_script': 'step-scripting',
        'review_script': 'step-scripting',
        'generate_video': 'step-producing',
        'generate_image': 'step-producing',
        'assemble_video': 'step-editing'
    };

    const stepId = mapping[type];
    if (!stepId) return;

    const stepEl = document.getElementById(stepId);
    if (!stepEl) return;

    if (status === 'in_progress') {
        stepEl.classList.add('active');
        stepEl.classList.remove('completed');
    } else if (status === 'completed') {
        stepEl.classList.remove('active');
        stepEl.classList.add('completed');
    }
}

function connectToSession(sessionId) {
    // Clear old state
    addLog(`Switching to session: ${sessionId}...`);
    logFeed.innerHTML = '';
    taskList.innerHTML = '';
    document.querySelectorAll('.step').forEach(s => s.classList.remove('active', 'completed'));
    gallery.style.display = 'none';

    const sessionRef = ref(db, `sessions/${sessionId}`);

    // Listen for agent updates
    onValue(ref(db, `sessions/${sessionId}/agents`), (snapshot) => {
        const agents = snapshot.val();
        if (agents) {
            Object.entries(agents).forEach(([id, data]) => {
                updateAgentCard(data.role, data);
            });
        }
    });

    // Listen for new messages
    onChildAdded(ref(db, `sessions/${sessionId}/messages`), (snapshot) => {
        const msg = snapshot.val();
        addLog(msg.msg_type, msg.msg_type === 'TASK_ASSIGNMENT' ? 'task' : 'message', msg.sender);
    });

    // Listen for tasks
    onValue(ref(db, `sessions/${sessionId}/tasks`), (snapshot) => {
        const tasks = snapshot.val();
        taskList.innerHTML = '';
        if (tasks) {
            const taskEntries = Object.entries(tasks);
            taskEntries.reverse().forEach(([id, t]) => {
                // Update Pipeline UI
                updatePipelineStep(id, t.type, t.status);

                // Update List
                const item = document.createElement('div');
                item.className = `log-item task ${t.status}`;
                item.innerHTML = `
                    <div style="font-weight:700">${t.type.replace('_', ' ').toUpperCase()}</div>
                    <div style="font-size:0.7rem; color:var(--text-secondary)">
                        Assigned: ${t.assigned_to} | Status: ${t.status}
                    </div>
                `;
                taskList.appendChild(item);

                // Handle final output
                if (t.type === 'assemble_video' && t.status === 'completed' && t.result) {
                    gallery.style.display = 'block';
                    outputPreview.innerHTML = `
                        <div style="padding: 1rem; background: rgba(16, 185, 129, 0.1); border-radius: 12px; border: 1px solid var(--status-idle);">
                            <p style="margin-bottom: 0.5rem;">✅ Video ready!</p>
                            <code>${t.result.video_path}</code>
                        </div>
                    `;
                }
            });
        }
    });
}

// Trigger Workflow
async function triggerWorkflow() {
    const prompt = promptInput.value.trim();
    if (!prompt) return;

    addLog("Sending start_workflow signal...", "system");
    
    const messagesRef = ref(db, `sessions/${currentSessionId}/messages`);
    const newMessageRef = push(messagesRef);
    
    await set(newMessageRef, {
        message_id: `msg_${Math.random().toString(36).substr(2, 9)}`,
        sender: "web_ui",
        receiver: "orchestrator",
        msg_type: "start_workflow",
        content: prompt,
        timestamp: new Date().toISOString()
    });

    promptInput.value = '';
    addLog("Workflow triggered successfully.", "system");
}

connectBtn.addEventListener('click', () => {
    currentSessionId = sessionIdInput.value;
    connectToSession(currentSessionId);
});

generateBtn.addEventListener('click', triggerWorkflow);

promptInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') triggerWorkflow();
});

// Initial connection
connectToSession(currentSessionId);
addLog("System Online. Awaiting commands.", "system");
