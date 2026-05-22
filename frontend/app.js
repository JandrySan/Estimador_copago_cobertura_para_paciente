// ── State ──────────────────────────────────────────────────────────────────
let history = [];
let isLoading = false;

// La URL del backend (en producción, pon tu URL de Railway/Render)
const API_URL = window.location.origin;

// ── Helpers ────────────────────────────────────────────────────────────────
function autoResize(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function scrollToBottom() {
  const win = document.getElementById('chat-window');
  win.scrollTop = win.scrollHeight;
}

function insertCedula(cedula) {
  const input = document.getElementById('user-input');
  input.value = cedula;
  input.focus();
  autoResize(input);
}

function handleKey(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
}

function sendQuick(text) {
  document.getElementById('user-input').value = text;
  sendMessage();
}

// ── Render messages ────────────────────────────────────────────────────────
function formatAgentText(text) {
  // Convertir líneas con ✅ 💊 🏥 📋 en bloques destacados
  const lines = text.split('\n');
  let html = '';
  let inBlock = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) { html += '<br/>'; continue; }

    const isResult = /^[✅💊🏥📋]/.test(trimmed);
    if (isResult && !inBlock) {
      html += '<div class="result-block">';
      inBlock = true;
    } else if (!isResult && inBlock) {
      html += '</div>';
      inBlock = false;
    }
    html += `<p>${trimmed}</p>`;
  }

  if (inBlock) html += '</div>';
  return html;
}

function appendMessage(role, text) {
  const win = document.getElementById('chat-window');

  // Quitar welcome si existe
  const welcome = win.querySelector('.welcome');
  if (welcome) welcome.remove();

  const div = document.createElement('div');
  div.className = `message ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = role === 'user' ? '👤' : '🩺';

  const bubble = document.createElement('div');
  bubble.className = 'bubble';

  if (role === 'agent') {
    bubble.innerHTML = formatAgentText(text);
  } else {
    bubble.textContent = text;
  }

  div.appendChild(avatar);
  div.appendChild(bubble);
  win.appendChild(div);
  scrollToBottom();
  return div;
}

function showTyping() {
  const win = document.getElementById('chat-window');
  const div = document.createElement('div');
  div.className = 'message agent';
  div.id = 'typing-indicator';

  const avatar = document.createElement('div');
  avatar.className = 'avatar';
  avatar.textContent = '🩺';

  const typing = document.createElement('div');
  typing.className = 'typing';
  typing.innerHTML = '<span></span><span></span><span></span>';

  div.appendChild(avatar);
  div.appendChild(typing);
  win.appendChild(div);
  scrollToBottom();
}

function removeTyping() {
  const t = document.getElementById('typing-indicator');
  if (t) t.remove();
}

// ── Send message ───────────────────────────────────────────────────────────
async function sendMessage() {
  if (isLoading) return;

  const input = document.getElementById('user-input');
  const text = input.value.trim();
  if (!text) return;

  input.value = '';
  input.style.height = 'auto';

  appendMessage('user', text);
  setLoading(true);
  showTyping();

  try {
    const res = await fetch(`${API_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: text, history })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Error del servidor');
    }

    const data = await res.json();
    history = data.history;

    removeTyping();
    appendMessage('agent', data.reply);

  } catch (err) {
    removeTyping();
    appendMessage('agent', `⚠️ Lo siento, ocurrió un error: ${err.message}. Verifica que el servidor esté corriendo.`);
  } finally {
    setLoading(false);
  }
}

function setLoading(val) {
  isLoading = val;
  document.getElementById('send-btn').disabled = val;
  document.getElementById('user-input').disabled = val;
}
