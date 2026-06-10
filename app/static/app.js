/* TWC offline demo frontend. No external libraries. */

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

let chatHistory = [];   // [{role, content}] for tab 1 continuity
let busy = false;
let selectedDoc = null;

/* ---------------- tabs ---------------- */
$$(".tab").forEach((btn) => {
  btn.addEventListener("click", () => {
    $$(".tab").forEach((b) => b.classList.remove("active"));
    $$(".panel").forEach((p) => p.classList.remove("active"));
    btn.classList.add("active");
    $("#panel-" + btn.dataset.tab).classList.add("active");
  });
});

/* ---------------- activity panel ---------------- */
const actLog = $("#activity-log");

function clearActivity() {
  actLog.innerHTML = "";
}

function addActivity(kind, head, body) {
  const div = document.createElement("div");
  div.className = "act act-" + kind;
  const h = document.createElement("div");
  h.className = "act-head";
  const icons = { tool: "⚙", result: "✓", think: "⚬", error: "⚠", status: "▸" };
  h.innerHTML = `<span class="act-icon">${icons[kind] || ""}</span> ${escapeHtml(head)}`;
  div.appendChild(h);
  if (body) {
    const b = document.createElement("div");
    b.className = "act-body";
    b.textContent = body;
    div.appendChild(b);
  }
  actLog.appendChild(div);
  actLog.parentElement.scrollTop = actLog.parentElement.scrollHeight;
  return div;
}

function setLive(on) {
  $("#live-dot").classList.toggle("on", on);
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ---------------- streaming runner ---------------- */
async function runAgent({ scenario, message, history = [], onToken, onThinking, onOutbox, onDone, onError }) {
  busy = true;
  setLive(true);
  let thinkingEl = null;

  try {
    const resp = await fetch("/api/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario, message, history }),
    });
    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let nl;
      while ((nl = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, nl).trim();
        buf = buf.slice(nl + 1);
        if (!line) continue;
        let ev;
        try { ev = JSON.parse(line); } catch { continue; }

        if (ev.type === "token") {
          thinkingEl = null;
          onToken && onToken(ev.text);
        } else if (ev.type === "thinking") {
          if (!thinkingEl) thinkingEl = addActivity("think", "Agent reasoning", "");
          const body = thinkingEl.querySelector(".act-body");
          body.textContent += ev.text;
          body.scrollTop = body.scrollHeight;
          onThinking && onThinking(ev.text);
        } else if (ev.type === "tool_call") {
          thinkingEl = null;
          const args = Object.keys(ev.args || {}).length
            ? JSON.stringify(ev.args, null, 1).replace(/[{}\n"]/g, " ").trim()
            : "";
          addActivity("tool", "Tool: " + ev.name, args);
        } else if (ev.type === "tool_result") {
          addActivity("result", "Result from " + ev.name, ev.preview);
        } else if (ev.type === "outbox") {
          onOutbox && onOutbox(ev.drafts);
        } else if (ev.type === "stats") {
          const badge = $("#stats-badge");
          const tools = ev.tool_calls ? ` · ${ev.tool_calls} tool calls` : "";
          badge.textContent = `⚡ ${ev.tok_s} tok/s · ${ev.tokens} tokens${tools} · ${ev.seconds}s`;
          badge.style.display = "";
        } else if (ev.type === "error") {
          addActivity("error", "Error", ev.text);
          onError && onError(ev.text);
        } else if (ev.type === "done") {
          onDone && onDone();
        }
      }
    }
  } catch (e) {
    addActivity("error", "Connection error", String(e));
    onError && onError(String(e));
  } finally {
    busy = false;
    setLive(false);
  }
}

/* ---------------- tab 1: business agent chat ---------------- */
const chatLog = $("#chat-log");

function addMsg(role, text, chatbotMode) {
  const div = document.createElement("div");
  div.className = "msg " + role + (chatbotMode ? " chatbot-mode" : "");
  if (role === "assistant") {
    const tag = document.createElement("span");
    tag.className = "mode-tag";
    tag.textContent = chatbotMode ? "PLAIN CHATBOT — no tools, no business context" : "AGENT — tools + business context";
    div.appendChild(tag);
  }
  const span = document.createElement("span");
  span.textContent = text;
  div.appendChild(span);
  chatLog.appendChild(div);
  chatLog.scrollTop = chatLog.scrollHeight;
  return span;
}

async function sendChat(text) {
  if (busy || !text.trim()) return;
  const agentMode = $("#agent-mode").checked;
  addMsg("user", text);
  $("#chat-input").value = "";
  const out = addMsg("assistant", "", !agentMode);
  let acc = "";

  await runAgent({
    scenario: agentMode ? "agent" : "chatbot",
    message: text,
    history: agentMode ? chatHistory : [],
    onToken: (t) => {
      acc += t;
      out.textContent = acc;
      chatLog.scrollTop = chatLog.scrollHeight;
    },
    onOutbox: renderOutbox,
    onDone: () => {
      if (agentMode) {
        chatHistory.push({ role: "user", content: text });
        chatHistory.push({ role: "assistant", content: acc });
      }
    },
  });
}

$("#chat-form").addEventListener("submit", (e) => {
  e.preventDefault();
  sendChat($("#chat-input").value);
});

$$(".chip").forEach((c) =>
  c.addEventListener("click", () => sendChat(c.textContent))
);

/* ---------------- tab 2: morning workflow ---------------- */
function renderInbox(inbox) {
  const list = $("#inbox-list");
  list.innerHTML = "";
  $("#inbox-count").textContent = "(" + inbox.length + ")";
  inbox.forEach((m) => {
    const div = document.createElement("div");
    div.className = "mail";
    div.innerHTML = `<div class="m-from">${escapeHtml(m.from)}</div>
      <div class="m-subj">${escapeHtml(m.subject)} · ${escapeHtml(m.received)}</div>
      <div class="m-body">${escapeHtml(m.body)}</div>`;
    div.addEventListener("click", () => div.classList.toggle("open"));
    list.appendChild(div);
  });
}

function renderOutbox(drafts) {
  const list = $("#outbox-list");
  list.innerHTML = "";
  $("#outbox-count").textContent = drafts.length ? "(" + drafts.length + ")" : "";
  drafts.forEach((d) => {
    const div = document.createElement("div");
    div.className = "mail draft open";
    div.innerHTML = `<div class="m-from">To: ${escapeHtml(d.to)}</div>
      <div class="m-subj">${escapeHtml(d.subject)}</div>
      <div class="m-body">${escapeHtml(d.body)}</div>`;
    div.addEventListener("click", () => div.classList.toggle("open"));
    list.appendChild(div);
  });
}

$("#run-workflow").addEventListener("click", async () => {
  if (busy) return;
  const btn = $("#run-workflow");
  btn.disabled = true;
  btn.textContent = "Running…";
  clearActivity();
  const box = $("#workflow-summary");
  box.innerHTML = "";
  let acc = "";

  await runAgent({
    scenario: "workflow",
    message:
      "Run the morning email workflow now. Triage the whole inbox, draft every reply that's needed, check anything against our records, then give me the owner summary.",
    onToken: (t) => {
      acc += t;
      box.textContent = acc;
      box.scrollTop = box.scrollHeight;
    },
    onOutbox: renderOutbox,
  });

  btn.disabled = false;
  btn.innerHTML = "&#9654; Run Morning Workflow";
});

/* ---------------- tab 3: documents ---------------- */
function renderDocs(docs) {
  const list = $("#doc-list");
  list.innerHTML = "";
  docs.forEach((name) => {
    const btn = document.createElement("button");
    btn.className = "doc-item";
    btn.textContent = "\u{1F4C4} " + name;
    btn.addEventListener("click", async () => {
      $$(".doc-item").forEach((d) => d.classList.remove("selected"));
      btn.classList.add("selected");
      selectedDoc = name;
      $("#analyze-doc").disabled = false;
      const r = await fetch("/api/document?name=" + encodeURIComponent(name));
      const j = await r.json();
      $("#doc-preview").textContent = j.text || "";
    });
    list.appendChild(btn);
  });
}

$("#analyze-doc").addEventListener("click", async () => {
  if (busy || !selectedDoc) return;
  const btn = $("#analyze-doc");
  btn.disabled = true;
  btn.textContent = "Analyzing…";
  clearActivity();
  const box = $("#doc-result");
  box.innerHTML = "";
  let acc = "";

  await runAgent({
    scenario: "documents",
    message:
      `Analyze the document "${selectedDoc}". Summarize it, extract the key facts and numbers, flag anything wrong or needing attention, and recommend next actions. Cross-check our business records where relevant.`,
    onToken: (t) => {
      acc += t;
      box.textContent = acc;
      box.scrollTop = box.scrollHeight;
    },
  });

  btn.disabled = false;
  btn.textContent = "Analyze document";
});

/* ---------------- reset ---------------- */
$("#reset-btn").addEventListener("click", async () => {
  if (busy) return;
  await fetch("/api/reset", { method: "POST" });
  chatHistory = [];
  chatLog.innerHTML = "";
  $("#workflow-summary").innerHTML = '<span class="placeholder">Run the workflow to generate the morning summary.</span>';
  $("#doc-result").innerHTML = '<span class="placeholder">Select a document and click Analyze.</span>';
  renderOutbox([]);
  clearActivity();
  actLog.innerHTML = '<div class="placeholder">Every step the agent takes shows up here — the difference between a chatbot and an agent.</div>';
});

/* ---------------- init ---------------- */
(async function init() {
  const r = await fetch("/api/state");
  const s = await r.json();
  $("#model-badge").textContent = "model: " + s.model;
  if (s.hardware_label) {
    const hw = $("#hw-badge");
    hw.textContent = s.hardware_label;
    hw.style.display = "";
  }
  renderInbox(s.inbox);
  renderOutbox(s.outbox);
  renderDocs(s.documents);
})();
