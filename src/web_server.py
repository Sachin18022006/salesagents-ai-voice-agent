"""FastAPI server for local webhook testing, REST conversation API, and interactive audio voice simulator UI."""

import uuid
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from src.state_machine import LAPVoiceStateMachine
from src.models import ConversationSession, RuntimeVariables

app = FastAPI(title="Home Credit LAP Voice Agent API", version="1.0.0")

# In-memory session store
sessions: Dict[str, LAPVoiceStateMachine] = {}


class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    utterance: str
    customer_name: Optional[str] = "Rajesh Sharma"
    agent_name: Optional[str] = "Priya"
    language_to_speak: Optional[str] = "English"


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    stage: str
    outcome: str
    checklist: Dict[str, Any]
    disqualification_reason: Optional[str] = None
    callback_preference: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok", "service": "Home Credit LAP Voice Agent"}


@app.get("/greeting")
def get_greeting(agent_name: str = "Priya", customer_name: str = "Rajesh Sharma", language: str = "English"):
    vars = RuntimeVariables(
        agent_name=agent_name,
        customer_name=customer_name,
        language_to_speak=language
    )
    sm = LAPVoiceStateMachine(ConversationSession(session_id=str(uuid.uuid4()), variables=vars))
    return {"greeting": sm.get_greeting_message()}


@app.post("/chat", response_model=ChatResponse)
def chat_turn(req: ChatRequest):
    sess_id = req.session_id or str(uuid.uuid4())
    if sess_id not in sessions:
        vars = RuntimeVariables(
            agent_name=req.agent_name or "Priya",
            customer_name=req.customer_name or "Rajesh Sharma",
            language_to_speak=req.language_to_speak or "English"
        )
        sessions[sess_id] = LAPVoiceStateMachine(
            ConversationSession(session_id=sess_id, variables=vars)
        )

    sm = sessions[sess_id]
    reply, session = sm.process_turn(req.utterance)

    return ChatResponse(
        session_id=sess_id,
        reply=reply,
        stage=session.stage.value,
        outcome=session.outcome.value,
        checklist=session.checklist.model_dump(),
        disqualification_reason=session.disqualification_reason,
        callback_preference=session.callback_preference
    )


@app.post("/webhook/retell")
def retell_webhook(payload: Dict[str, Any]):
    event = payload.get("event")
    call_id = payload.get("call", {}).get("call_id")
    print(f"[RETELL WEBHOOK] Event: {event}, Call ID: {call_id}")
    return {"status": "received", "event": event, "call_id": call_id}


@app.get("/", response_class=HTMLResponse)
def demo_ui():
    """Interactive web interface with real Text-to-Speech audio and Microphone speech recognition."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Home Credit LAP Voice Agent - Audio Simulator</title>
    <style>
        :root {
            --bg: #090d16;
            --surface: #131d31;
            --surface-card: #1e293b;
            --primary: #3b82f6;
            --accent: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text: #f8fafc;
            --text-dim: #94a3b8;
        }
        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px 16px;
            display: flex;
            justify-content: center;
        }
        .container {
            width: 100%;
            max-width: 950px;
            background: var(--surface);
            border-radius: 14px;
            padding: 24px;
            box-shadow: 0 15px 35px rgba(0,0,0,0.6);
            border: 1px solid #1e293b;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 12px;
            border-bottom: 1px solid #334155;
            padding-bottom: 16px;
            margin-bottom: 16px;
        }
        h1 { margin: 0; color: #60a5fa; font-size: 20px; font-weight: 700; }
        .audio-status-pill {
            background: #064e3b;
            color: #34d399;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        .meta-bar {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            margin-bottom: 18px;
            background: var(--surface-card);
            padding: 12px 16px;
            border-radius: 10px;
            font-size: 13px;
            color: var(--text-dim);
            align-items: center;
        }
        .meta-bar strong { color: #f1f5f9; }
        .config-input {
            background: #0f172a;
            border: 1px solid #475569;
            color: #fff;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            width: 110px;
        }
        .chat-box {
            height: 380px;
            overflow-y: auto;
            border: 1px solid #334155;
            border-radius: 10px;
            padding: 16px;
            background: #060911;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .bubble {
            max-width: 80%;
            padding: 12px 16px;
            border-radius: 10px;
            font-size: 14px;
            line-height: 1.45;
            position: relative;
        }
        .bubble.agent {
            background: #172554;
            align-self: flex-start;
            border-left: 4px solid var(--primary);
            color: #e0f2fe;
        }
        .bubble.customer {
            background: #064e3b;
            align-self: flex-end;
            border-right: 4px solid var(--accent);
            color: #ecfdf5;
        }
        .speak-btn {
            background: #1e40af;
            border: none;
            color: #93c5fd;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 4px;
            cursor: pointer;
            margin-top: 6px;
            display: inline-block;
        }
        .speak-btn:hover { background: #2563eb; color: #fff; }
        .input-row {
            display: flex;
            gap: 10px;
            margin-top: 16px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px 14px;
            border-radius: 8px;
            border: 1px solid #475569;
            background: #0f172a;
            color: #fff;
            font-size: 14px;
        }
        input[type="text"]:focus { outline: none; border-color: var(--primary); }
        button.btn-primary {
            background: var(--primary);
            color: white;
            border: none;
            padding: 12px 20px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
        }
        button.btn-mic {
            background: #dc2626;
            color: white;
            border: none;
            padding: 12px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        button.btn-mic.listening {
            animation: pulse 1.2s infinite;
            background: #991b1b;
        }
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        .status-grid {
            margin-top: 20px;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 10px;
        }
        .status-card {
            background: var(--surface-card);
            padding: 10px 14px;
            border-radius: 8px;
            border: 1px solid #334155;
        }
        .status-title { color: var(--text-dim); font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; }
        .status-val { font-size: 13px; font-weight: 700; margin-top: 4px; color: #cbd5e1; }
        .badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; }
        .badge-green { background: #065f46; color: #34d399; }
        .badge-red { background: #7f1d1d; color: #f87171; }
        .badge-blue { background: #1e3a8a; color: #93c5fd; }
        .audio-controls {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: var(--text-dim);
            margin-top: 10px;
        }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <div>
            <h1>Home Credit LAP Voice Agent — Audio Simulator</h1>
            <div style="font-size: 12px; color: var(--text-dim); margin-top: 4px;">Natural Voice Audio with Real Browser Speech Synthesis & Microphone Input</div>
        </div>
        <div class="audio-status-pill" id="voiceStatus">
            <span>🔊</span> <span id="voiceStatusText">Voice Audio Ready</span>
        </div>
    </div>

    <div class="meta-bar">
        <span>Target: <strong>₹75,00,000 LAP</strong></span>
        <span>Lead Voice: <input type="text" id="agentNameInput" value="Priya" class="config-input" onchange="restartSession()"> (Female)</span>
        <span>Customer: <input type="text" id="customerNameInput" value="Rajesh Sharma" class="config-input" onchange="restartSession()"></span>
        <span>Stage: <span id="currentStage" class="badge badge-blue">GREETING</span></span>
        <span>Outcome: <span id="currentOutcome" class="badge badge-blue">IN_PROGRESS</span></span>
    </div>

    <div class="chat-box" id="chatBox">
        <div class="bubble agent" id="initialGreetingBubble">
            <div id="initialGreetingText">Hello, good morning, am I speaking with Rajesh Sharma? I'm Priya calling from Home Credit.</div>
            <button class="speak-btn" onclick="speakText(document.getElementById('initialGreetingText').innerText)">▶ Play Voice</button>
        </div>
    </div>

    <div class="input-row">
        <input type="text" id="userInput" placeholder="Type or click 'Speak via Mic' to speak..." autofocus onkeydown="if(event.key==='Enter') sendUtterance()">
        <button class="btn-mic" id="micBtn" onclick="toggleMic()">🎙️ Speak via Mic</button>
        <button class="btn-primary" onclick="sendUtterance()">Send</button>
    </div>

    <div class="audio-controls">
        <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
            <input type="checkbox" id="autoVoiceToggle" checked>
            <span>Automatically speak agent response out loud</span>
        </label>
        <span style="margin-left:auto; cursor:pointer; color:#60a5fa;" onclick="restartSession()">🔄 Restart Call</span>
    </div>

    <div class="status-grid" id="checklistGrid">
        <div class="status-card"><div class="status-title">1. Property Type</div><div id="f_property_type" class="status-val">-</div></div>
        <div class="status-card"><div class="status-title">2. Ownership Status</div><div id="f_ownership_status" class="status-val">-</div></div>
        <div class="status-card"><div class="status-title">3. Original Docs</div><div id="f_original_documents_available" class="status-val">-</div></div>
        <div class="status-card"><div class="status-title">4. Loan Amount</div><div id="f_requested_loan_amount" class="status-val">-</div></div>
        <div class="status-card"><div class="status-title">5. Occupation & Mode</div><div id="f_occupation_and_income_mode" class="status-val">-</div></div>
        <div class="status-card"><div class="status-title">6. Market Value</div><div id="f_property_market_value" class="status-val">-</div></div>
        <div class="status-card"><div class="status-title">7. Tenure (Years)</div><div id="f_requested_tenure_years" class="status-val">-</div></div>
    </div>
</div>

<script>
let sessionId = "sim-" + Math.floor(Math.random() * 100000);
let recognition = null;
let isListening = false;
let selectedVoice = null;

// Initialize speech synthesis voices
function initVoices() {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.onvoiceschanged = () => {
            const voices = window.speechSynthesis.getVoices();
            // Look for Indian English female voice first, or natural female English voice
            selectedVoice = voices.find(v => v.lang.includes('en-IN') && (v.name.includes('Female') || v.name.includes('Heera') || v.name.includes('Google') || v.name.includes('Priya') || v.name.includes('Neerja')))
                || voices.find(v => v.lang.includes('en-IN'))
                || voices.find(v => v.name.includes('Female') || v.name.includes('Zira') || v.name.includes('Samantha'))
                || voices[0];
            if (selectedVoice) {
                document.getElementById('voiceStatusText').innerText = "Voice: " + selectedVoice.name;
            }
        };
    }
}
initVoices();

// Text to Speech playback
function speakText(text) {
    if (!('speechSynthesis' in window)) {
        alert("Your browser does not support Web Speech Audio. Please use Chrome or Edge.");
        return;
    }
    window.speechSynthesis.cancel(); // Stop any ongoing speech
    const cleanText = text.replace(/₹/g, "Rupees ").replace(/\*/g, "");
    const utterance = new SpeechSynthesisUtterance(cleanText);
    if (selectedVoice) {
        utterance.voice = selectedVoice;
    }
    utterance.rate = 1.0;
    utterance.pitch = 1.05; // Slightly higher pitch for female lead tone
    window.speechSynthesis.speak(utterance);
}

// Microphone Speech-to-Text
function setupSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
        recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.interimResults = false;
        recognition.lang = 'en-IN';

        recognition.onstart = () => {
            isListening = true;
            const micBtn = document.getElementById('micBtn');
            micBtn.innerText = "Listening...";
            micBtn.classList.add('listening');
        };

        recognition.onresult = (event) => {
            const transcript = event.results[0][0].transcript;
            document.getElementById('userInput').value = transcript;
            sendUtterance();
        };

        recognition.onerror = (event) => {
            console.error("Speech recognition error:", event.error);
            stopMic();
        };

        recognition.onend = () => {
            stopMic();
        };
    }
}
setupSpeechRecognition();

function toggleMic() {
    if (!recognition) {
        alert("Microphone voice input requires Google Chrome, Edge, or a browser supporting Web Speech API.");
        return;
    }
    if (isListening) {
        recognition.stop();
        stopMic();
    } else {
        recognition.start();
    }
}

function stopMic() {
    isListening = false;
    const micBtn = document.getElementById('micBtn');
    micBtn.innerText = "🎙️ Speak via Mic";
    micBtn.classList.remove('listening');
}

async function sendUtterance() {
    const input = document.getElementById('userInput');
    const text = input.value.trim();
    if (!text) return;

    appendBubble("customer", text);
    input.value = "";

    const agentName = document.getElementById('agentNameInput').value.trim() || "Priya";
    const customerName = document.getElementById('customerNameInput').value.trim() || "Rajesh Sharma";

    try {
        const res = await fetch("/chat", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({
                session_id: sessionId,
                utterance: text,
                agent_name: agentName,
                customer_name: customerName
            })
        });
        const data = await res.json();
        appendBubble("agent", data.reply);
        updateUI(data);

        // Auto play audio voice if enabled
        if (document.getElementById('autoVoiceToggle').checked) {
            speakText(data.reply);
        }
    } catch (err) {
        appendBubble("agent", "[Error communicating with agent engine]");
    }
}

function appendBubble(speaker, text) {
    const chat = document.getElementById("chatBox");
    const div = document.createElement("div");
    div.className = "bubble " + speaker;
    
    if (speaker === "agent") {
        div.innerHTML = `<div>${text}</div><button class="speak-btn" onclick="speakText(this.previousElementSibling.innerText)">▶ Play Voice</button>`;
    } else {
        div.innerText = text;
    }
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
}

function updateUI(data) {
    document.getElementById("currentStage").innerText = data.stage;
    const outcomeEl = document.getElementById("currentOutcome");
    outcomeEl.innerText = data.outcome;
    if (data.outcome === "qualified_handoff") {
        outcomeEl.className = "badge badge-green";
    } else if (data.outcome.startsWith("disqualified_")) {
        outcomeEl.className = "badge badge-red";
    } else if (data.outcome === "loan_transfer_referral") {
        outcomeEl.className = "badge badge-blue";
    }

    const c = data.checklist;
    if (c) {
        for (const key in c) {
            const el = document.getElementById("f_" + key);
            if (el && c[key].is_answered) {
                let displayVal = c[key].parsed_value;
                if (typeof displayVal === 'object' && displayVal !== null) {
                    displayVal = JSON.stringify(displayVal);
                } else if (key.includes('amount') || key.includes('value')) {
                    displayVal = "₹" + Number(displayVal).toLocaleString('en-IN');
                }
                el.innerText = displayVal;
                el.style.color = c[key].is_valid ? "#34d399" : "#f87171";
            }
        }
    }
}

async function restartSession() {
    sessionId = "sim-" + Math.floor(Math.random() * 100000);
    const agentName = document.getElementById('agentNameInput').value.trim() || "Priya";
    const customerName = document.getElementById('customerNameInput').value.trim() || "Rajesh Sharma";

    const res = await fetch(`/greeting?agent_name=${encodeURIComponent(agentName)}&customer_name=${encodeURIComponent(customerName)}`);
    const data = await res.json();

    const chat = document.getElementById("chatBox");
    chat.innerHTML = `<div class="bubble agent"><div>${data.greeting}</div><button class="speak-btn" onclick="speakText(this.previousElementSibling.innerText)">▶ Play Voice</button></div>`;
    
    document.getElementById("currentStage").innerText = "GREETING";
    document.getElementById("currentOutcome").innerText = "IN_PROGRESS";
    document.getElementById("currentOutcome").className = "badge badge-blue";

    const fields = ["property_type", "ownership_status", "original_documents_available", "requested_loan_amount", "occupation_and_income_mode", "property_market_value", "requested_tenure_years"];
    fields.forEach(f => {
        const el = document.getElementById("f_" + f);
        if (el) { el.innerText = "-"; el.style.color = "#cbd5e1"; }
    });

    if (document.getElementById('autoVoiceToggle').checked) {
        speakText(data.greeting);
    }
}

// On initial page load: play initial greeting if user clicked anywhere
window.addEventListener('click', () => {
    // Audio context unlocked
}, { once: true });
</script>
</body>
</html>
"""
