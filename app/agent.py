"""
Agent engine for the TWC offline demo.
Runs a tool-use loop against a local Ollama instance. Python stdlib only.
"""

import ast
import json
import operator
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

# In-memory quotes: customer quotes the agent builds during a session.
QUOTES = []

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


_CALC_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow,
}


def _calc_eval(node):
    if isinstance(node, ast.Expression):
        return _calc_eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        v = _calc_eval(node.operand)
        return -v if isinstance(node.op, ast.USub) else v
    if isinstance(node, ast.BinOp) and type(node.op) in _CALC_OPS:
        left, right = _calc_eval(node.left), _calc_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("exponent too large")
        return _CALC_OPS[type(node.op)](left, right)
    raise ValueError(f"unsupported syntax: {type(node).__name__}")


def tool_calculate(args):
    # Models sprinkle $ signs and thousands separators into expressions;
    # strip them rather than bouncing the call.
    expr = str(args.get("expression", "")).replace("$", "").replace(",", "").strip()
    if not expr:
        return ('ERROR: calculate takes exactly one argument named "expression" '
                'containing the arithmetic as a string, like '
                '{"expression": "12*(3*115 + 85*1.15)"}. Try again.')
    try:
        value = _calc_eval(ast.parse(expr, mode="eval"))
    except ZeroDivisionError:
        return "ERROR: division by zero."
    except (ValueError, SyntaxError) as e:
        return f"ERROR: cannot evaluate ({e}). Use plain arithmetic like 12 * (3*115 + 85*1.15)."
    rounded = round(value, 2)
    if rounded == int(rounded):
        rounded = int(rounded)
    return f"{expr} = {rounded:,}"


def tool_save_quote(args):
    missing = [k for k in ("customer", "line_items", "total", "lead_time")
               if not str(args.get(k, "")).strip()]
    if missing:
        return (f"ERROR: quote NOT saved - missing field(s): {', '.join(missing)}. "
                "Call save_quote again with every field filled in.")
    try:
        subtotal = float(args.get("subtotal", 0))
        total = float(args.get("total", 0))
    except (TypeError, ValueError):
        return "ERROR: quote NOT saved - subtotal and total must be numbers."
    if total < subtotal:
        return (f"ERROR: quote NOT saved - total ({total}) is less than subtotal "
                f"({subtotal}). Recompute with the calculate tool and try again.")
    quote = {
        "customer": str(args.get("customer", "")),
        "line_items": str(args.get("line_items", "")),
        "subtotal": args.get("subtotal", 0),
        "expedite_fee": args.get("expedite_fee", 0),
        "total": args.get("total", 0),
        "lead_time": str(args.get("lead_time", "")),
        "valid_days": args.get("valid_days", 30),
        "notes": str(args.get("notes", "")),
    }
    QUOTES.append(quote)
    return f"Quote saved for {quote['customer']} ({len(QUOTES)} total)."


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
    "calculate": tool_calculate,
    "save_quote": tool_save_quote,
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
            "to": {"type": "string", "description": "Recipient name and email address exactly as shown in the original email's From line, e.g. 'Jenny Tran <jtran@nechesindustrial.com>'"},
            "subject": {"type": "string", "description": "Reply subject line, e.g. 'Re: ...'"},
            "body": {"type": "string", "description": "Full email body in the company voice"},
        }, "required": ["to", "subject", "body"]},
    }},
    {"type": "function", "function": {
        "name": "calculate",
        "description": "Evaluate an arithmetic expression exactly. Use this for ALL math - never compute numbers in your head. Supports + - * / % ** and parentheses.",
        "parameters": {"type": "object", "properties": {
            "expression": {"type": "string", "description": "e.g. 12 * (3*115 + 85*1.15)"},
        }, "required": ["expression"]},
    }},
    {"type": "function", "function": {
        "name": "save_quote",
        "description": "Save the finished customer quote for owner review. Every number must come from the calculate tool.",
        "parameters": {"type": "object", "properties": {
            "customer": {"type": "string", "description": "Customer/company name"},
            "line_items": {"type": "string", "description": "One line per item: 'qty x description @ $unit each = $line_total'. Include material as its own line when priced separately."},
            "subtotal": {"type": "number", "description": "Sum of line items before any fees"},
            "expedite_fee": {"type": "number", "description": "Dollar amount of any expedite fee. 0 if none or waived (explain waivers in notes)."},
            "total": {"type": "number"},
            "lead_time": {"type": "string", "description": "Realistic delivery window from the lead-time table, e.g. '1-2 weeks'"},
            "valid_days": {"type": "integer", "description": "30 normally; 10 for exotic materials (Inconel, Monel)"},
            "notes": {"type": "string", "description": "Contract terms applied, fee waivers, deposit requirements, anything the owner should double-check"},
        }, "required": ["customer", "line_items", "subtotal", "total", "lead_time"]},
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
    "quote": ["list_context_files", "read_context_file",
              "calculate", "save_quote"],
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
        "The inbox list, pricing/lead-time sheet, and email voice policy are "
        "already loaded above as tool results. Now:\n"
        "1. For each email in the inbox, call read_email with its id, one at a "
        "time.\n"
        "2. Triage it: URGENT (plant-down, quality complaint), NORMAL (quotes, "
        "new customers), or LOW (vendor pitches).\n"
        "3. If it deserves a reply, call save_draft, following the company "
        "voice and the policies (rush policy, expedite fee waivers, new "
        "customer terms, vendor pitch handling). Some customers have special "
        "contract terms - check the pricing sheet carefully.\n"
        "4. If an email references an invoice, call read_document to verify it "
        "against the contract terms before replying.\n"
        "5. After ALL emails are handled, write the MORNING SUMMARY for the "
        "owner as plain text: each email, its priority, what you did, and "
        "anything needing a human decision.\n\n"
        "HARD RULES:\n"
        "- Every action MUST be a real tool call. NEVER write tool names, "
        "JSON, or tool syntax inside your text reply.\n"
        "- Do not invent emails, names, or facts. Only use what tools return.\n"
        "- Your only text output is the final MORNING SUMMARY, after the last "
        "tool call.\n\n"
        + VOICE_RULE
    ),
    "quote": (
        "You are the business agent for Gulf Coast Machining Co., a CNC machine "
        "shop in Beaumont, Texas. You are building a CUSTOMER QUOTE from a "
        "request.\n\n"
        "Do this, in order:\n"
        "1. Read pricing-and-leadtimes.md with the read_context_file tool. "
        "Every price and lead time comes from there.\n"
        "2. Use the calculate tool once per line item, passing one full "
        "arithmetic expression built from the pricing sheet rules (shop rate "
        "per hour, material at cost + 15%, repeat parts about 20% cheaper "
        "than first run, expedite fees, per-customer contract terms). NEVER "
        "do arithmetic yourself - language models get math wrong, the "
        "calculator does not.\n"
        "3. Call calculate again for the subtotal and total.\n"
        "4. Call save_quote with the finished quote. Pick the lead time from "
        "the lead-time table. Set valid_days to 10 for exotic materials "
        "(Inconel, Monel), 30 otherwise. Note any contract terms you applied "
        "(like waived expedite fees) in notes.\n"
        "5. Only after save_quote succeeds, write a 2-3 sentence summary for "
        "the owner: the total, the lead time, and anything to double-check.\n\n"
        "HARD RULES:\n"
        "- calculate and save_quote are real tools. CALL them. NEVER write "
        "tool names, JSON, or tool syntax inside your text reply.\n"
        "- Never invent prices. Every number comes from the pricing sheet or "
        "the customer's request, combined via the calculate tool.\n"
        "- Add an expedite fee ONLY if the customer asked for rush or "
        "emergency turnaround. Normal orders get no fee.\n"
        "- Check the pricing sheet for customer-specific contract terms "
        "(e.g. expedite fee waivers) before adding fees."
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
        "options": {"num_ctx": CONFIG.get("num_ctx", 16384),
                    "temperature": CONFIG.get("temperature", 0.2)},
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

    # Workflow prefetch: load the inbox and key context files into the
    # conversation as real tool exchanges. Deterministic, instant activity in
    # the UI, and small models don't have to be trusted to fetch them.
    prefetch = []
    if scenario == "workflow":
        prefetch = [
            ("list_inbox", {}),
            ("read_context_file", {"filename": "pricing-and-leadtimes.md"}),
            ("read_context_file", {"filename": "voice-and-policies.md"}),
        ]

    start = time.time()
    total_tokens = 0
    total_eval_ns = 0
    total_tool_calls = 0

    try:
        if prefetch:
            calls = [{"function": {"name": n, "arguments": a}}
                     for n, a in prefetch]
            messages.append({"role": "assistant", "content": "",
                             "tool_calls": calls})
            for name, args in prefetch:
                total_tool_calls += 1
                yield {"type": "tool_call", "name": name, "args": args}
                result = TOOL_IMPLS[name](args)
                preview = (result if len(result) <= 400
                           else result[:400] + " ...")
                yield {"type": "tool_result", "name": name, "preview": preview}
                messages.append({"role": "tool", "content": result,
                                 "tool_name": name})

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
                if name == "save_quote":
                    yield {"type": "quote", "quotes": list(QUOTES)}

                messages.append({"role": "tool", "content": result,
                                 "tool_name": name})

        yield {"type": "error", "text": "Agent hit the max turn limit."}
    except urllib.error.URLError as e:
        yield {"type": "error",
               "text": f"Cannot reach Ollama at {CONFIG['ollama_url']} - is it "
                       f"running? ({e})"}
    except Exception as e:  # surface anything else to the UI
        yield {"type": "error", "text": f"{type(e).__name__}: {e}"}
