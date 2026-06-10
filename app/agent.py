"""
Agent engine for the TWC offline demo.
Runs a tool-use loop against a local Ollama instance. Python stdlib only.
"""

import json
import os
import time
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONTEXT_DIR = os.path.join(DATA_DIR, "context")
DOCS_DIR = os.path.join(DATA_DIR, "documents")

with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

# In-memory outbox: drafts the agent saves during a session.
OUTBOX = []

MAX_TURNS = 16  # safety cap on the agent loop


# ---------------------------------------------------------------- tools

def _safe_name(name, folder):
    """Resolve a filename inside a folder, blocking path escapes."""
    base = os.path.basename(name)
    path = os.path.join(folder, base)
    return path if os.path.isfile(path) else None


def tool_list_context_files(args):
    return "\n".join(sorted(os.listdir(CONTEXT_DIR)))


def tool_read_context_file(args):
    path = _safe_name(args.get("filename", ""), CONTEXT_DIR)
    if not path:
        return "ERROR: no such context file. Use list_context_files to see what exists."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def tool_list_inbox(args):
    with open(os.path.join(DATA_DIR, "inbox.json"), "r", encoding="utf-8") as f:
        inbox = json.load(f)
    lines = ["id | from | subject | received"]
    for m in inbox:
        lines.append(f'{m["id"]} | {m["from"]} | {m["subject"]} | {m["received"]}')
    return "\n".join(lines)


def tool_read_email(args):
    with open(os.path.join(DATA_DIR, "inbox.json"), "r", encoding="utf-8") as f:
        inbox = json.load(f)
    for m in inbox:
        if m["id"] == int(args.get("id", -1)):
            return (f'From: {m["from"]}\nSubject: {m["subject"]}\n'
                    f'Received: {m["received"]}\n\n{m["body"]}')
    return "ERROR: no email with that id."


def tool_save_draft(args):
    draft = {
        "to": args.get("to", ""),
        "subject": args.get("subject", ""),
        "body": args.get("body", ""),
    }
    OUTBOX.append(draft)
    return f"Draft saved to outbox ({len(OUTBOX)} drafts total)."


def tool_list_documents(args):
    return "\n".join(sorted(os.listdir(DOCS_DIR)))


def tool_read_document(args):
    path = _safe_name(args.get("filename", ""), DOCS_DIR)
    if not path:
        return "ERROR: no such document. Use list_documents to see what exists."
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


TOOL_IMPLS = {
    "list_context_files": tool_list_context_files,
    "read_context_file": tool_read_context_file,
    "list_inbox": tool_list_inbox,
    "read_email": tool_read_email,
    "save_draft": tool_save_draft,
    "list_documents": tool_list_documents,
    "read_document": tool_read_document,
}

TOOL_DEFS = [
    {"type": "function", "function": {
        "name": "list_context_files",
        "description": "List the business context files available (profile, pricing, voice/policies).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "read_context_file",
        "description": "Read one business context file by filename.",
        "parameters": {"type": "object", "properties": {
            "filename": {"type": "string", "description": "e.g. pricing-and-leadtimes.md"},
        }, "required": ["filename"]},
    }},
    {"type": "function", "function": {
        "name": "list_inbox",
        "description": "List the emails currently in the company inbox (id, from, subject).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "read_email",
        "description": "Read the full body of one inbox email by id.",
        "parameters": {"type": "object", "properties": {
            "id": {"type": "integer", "description": "email id from list_inbox"},
        }, "required": ["id"]},
    }},
    {"type": "function", "function": {
        "name": "save_draft",
        "description": "Save a reply draft to the outbox for human review. Use the company email voice.",
        "parameters": {"type": "object", "properties": {
            "to": {"type": "string"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
        }, "required": ["to", "subject", "body"]},
    }},
    {"type": "function", "function": {
        "name": "list_documents",
        "description": "List documents available for analysis (invoices, reports, letters).",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }},
    {"type": "function", "function": {
        "name": "read_document",
        "description": "Read the full text of one document by filename.",
        "parameters": {"type": "object", "properties": {
            "filename": {"type": "string"},
        }, "required": ["filename"]},
    }},
]

# Which tools each scenario gets
SCENARIO_TOOLS = {
    "agent": ["list_context_files", "read_context_file", "save_draft"],
    "workflow": ["list_context_files", "read_context_file", "list_inbox",
                 "read_email", "save_draft", "list_documents", "read_document"],
    "documents": ["list_context_files", "read_context_file",
                  "list_documents", "read_document"],
    "chatbot": [],  # the "plain chatbot" toggle: same model, no tools, no context
}


# ---------------------------------------------------------------- prompts

VOICE_RULE = (
    "Write emails in the company voice defined in voice-and-policies.md. "
    "Plain, short, friendly, no corporate filler."
)

SYSTEM_PROMPTS = {
    "agent": (
        "You are the business agent for Gulf Coast Machining Co., a CNC machine "
        "shop in Beaumont, Texas. You help the owner (Dale) and office manager "
        "(Cheryl) with questions, quotes, and email drafts.\n\n"
        "You have tools to read the company's context files (business profile, "
        "pricing and lead times, email voice and policies). ALWAYS read the "
        "relevant context file before answering questions about pricing, lead "
        "times, policies, or customers. Never guess numbers.\n\n"
        + VOICE_RULE + "\n\n"
        "Keep answers concise and practical. If asked to draft an email, save "
        "it with save_draft. You are talking to shop staff, not customers."
    ),
    "chatbot": (
        "You are a general-purpose AI chatbot. You have no tools, no files, and "
        "no knowledge of any specific business. Answer questions as best you "
        "can from general knowledge. If asked about a specific company's "
        "pricing, lead times, customers, or policies, you must admit you have "
        "no access to that information. Keep answers brief."
    ),
    "workflow": (
        "You are the business agent for Gulf Coast Machining Co., a CNC machine "
        "shop in Beaumont, Texas. You are running the MORNING EMAIL WORKFLOW.\n\n"
        "Follow these steps exactly:\n"
        "1. Read the business context files first (pricing-and-leadtimes.md and "
        "voice-and-policies.md at minimum).\n"
        "2. List the inbox, then read every email.\n"
        "3. Triage each email: URGENT (plant-down, quality complaint), NORMAL "
        "(quotes, new customers), or LOW (vendor pitches).\n"
        "4. For every email that deserves a reply, draft one with save_draft, "
        "following the company voice and the policies (rush policy, expedite "
        "fee waivers, new customer terms, vendor pitch handling). Check the "
        "policies carefully - some customers have special contract terms.\n"
        "5. If an email references an invoice or document you can check, check it.\n"
        "6. Finish with a short MORNING SUMMARY for the owner: each email, its "
        "priority, what you did, and anything that needs a human decision.\n\n"
        + VOICE_RULE
    ),
    "documents": (
        "You are the business agent for Gulf Coast Machining Co., a CNC machine "
        "shop in Beaumont, Texas. The user will ask you to analyze a document. "
        "Read it with your tools, then provide: a 2-3 sentence summary, the key "
        "facts and numbers extracted, anything that looks wrong or needs "
        "attention, and recommended next actions for a small business owner. "
        "Cross-check against the business context files when relevant (for "
        "example, contract terms, materials we buy, our policies). Be concrete "
        "and brief - this is for a busy shop owner."
    ),
}


# ---------------------------------------------------------------- ollama

def _ollama_chat_stream(messages, tools):
    """POST to Ollama /api/chat with streaming. Yields parsed NDJSON chunks."""
    payload = {
        "model": CONFIG["model"],
        "messages": messages,
        "stream": True,
        "options": {"num_ctx": CONFIG.get("num_ctx", 16384)},
    }
    if tools:
        payload["tools"] = tools
    req = urllib.request.Request(
        CONFIG["ollama_url"].rstrip("/") + "/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        for raw in resp:
            line = raw.decode("utf-8").strip()
            if line:
                yield json.loads(line)


# ---------------------------------------------------------------- loop

def run_agent(scenario, history, user_message):
    """
    Generator. Runs the agent loop and yields event dicts:
      {"type": "status",      "text": ...}
      {"type": "thinking",    "text": ...}            (model reasoning, if any)
      {"type": "token",       "text": ...}            (assistant text chunk)
      {"type": "tool_call",   "name": ..., "args": {...}}
      {"type": "tool_result", "name": ..., "preview": ...}
      {"type": "outbox",      "drafts": [...]}        (after save_draft)
      {"type": "done"}
      {"type": "error",       "text": ...}
    """
    system = SYSTEM_PROMPTS.get(scenario, SYSTEM_PROMPTS["agent"])
    tool_names = SCENARIO_TOOLS.get(scenario, [])
    tools = [t for t in TOOL_DEFS if t["function"]["name"] in tool_names]

    messages = [{"role": "system", "content": system}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    start = time.time()
    total_tokens = 0
    total_eval_ns = 0
    total_tool_calls = 0

    try:
        for turn in range(MAX_TURNS):
            content_parts = []
            thinking_parts = []
            tool_calls = []

            for chunk in _ollama_chat_stream(messages, tools):
                msg = chunk.get("message", {})
                if msg.get("thinking"):
                    thinking_parts.append(msg["thinking"])
                    yield {"type": "thinking", "text": msg["thinking"]}
                if msg.get("content"):
                    content_parts.append(msg["content"])
                    yield {"type": "token", "text": msg["content"]}
                if msg.get("tool_calls"):
                    tool_calls.extend(msg["tool_calls"])
                if chunk.get("error"):
                    yield {"type": "error", "text": chunk["error"]}
                    return
                if chunk.get("done"):
                    total_tokens += chunk.get("eval_count", 0)
                    total_eval_ns += chunk.get("eval_duration", 0)

            assistant_msg = {"role": "assistant",
                             "content": "".join(content_parts)}
            if tool_calls:
                assistant_msg["tool_calls"] = tool_calls
            messages.append(assistant_msg)

            if not tool_calls:
                tok_s = (total_tokens / (total_eval_ns / 1e9)
                         if total_eval_ns else 0)
                yield {"type": "stats",
                       "tokens": total_tokens,
                       "tok_s": round(tok_s, 1),
                       "seconds": round(time.time() - start, 1),
                       "tool_calls": total_tool_calls}
                yield {"type": "done"}
                return

            for tc in tool_calls:
                fn = tc.get("function", {})
                name = fn.get("name", "")
                args = fn.get("arguments", {}) or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}
                total_tool_calls += 1
                yield {"type": "tool_call", "name": name, "args": args}

                impl = TOOL_IMPLS.get(name)
                result = impl(args) if impl else f"ERROR: unknown tool {name}"
                preview = result if len(result) <= 400 else result[:400] + " ..."
                yield {"type": "tool_result", "name": name, "preview": preview}
                if name == "save_draft":
                    yield {"type": "outbox", "drafts": list(OUTBOX)}

                messages.append({"role": "tool", "content": result,
                                 "tool_name": name})

        yield {"type": "error", "text": "Agent hit the max turn limit."}
    except urllib.error.URLError as e:
        yield {"type": "error",
               "text": f"Cannot reach Ollama at {CONFIG['ollama_url']} - is it "
                       f"running? ({e})"}
    except Exception as e:  # surface anything else to the UI
        yield {"type": "error", "text": f"{type(e).__name__}: {e}"}
