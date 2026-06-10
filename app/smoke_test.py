"""
Smoke test for the TWC demo. Run: python smoke_test.py
Checks everything except the browser: data files, Ollama connectivity,
model availability, and one real agent loop with a tool call.
"""

import json
import os
import sys
import urllib.request

import agent

OK = "  [ok]"
FAIL = "  [FAIL]"
failures = 0


def check(label, fn):
    global failures
    try:
        detail = fn()
        print(f"{OK} {label}" + (f" - {detail}" if detail else ""))
    except Exception as e:
        failures += 1
        print(f"{FAIL} {label}: {e}")


def data_files():
    for f in ["inbox.json"]:
        assert os.path.isfile(os.path.join(agent.DATA_DIR, f)), f
    n_ctx = len(os.listdir(agent.CONTEXT_DIR))
    n_doc = len(os.listdir(agent.DOCS_DIR))
    with open(os.path.join(agent.DATA_DIR, "inbox.json"), encoding="utf-8") as fh:
        inbox = json.load(fh)
    return f"{n_ctx} context files, {n_doc} documents, {len(inbox)} emails"


def ollama_up():
    url = agent.CONFIG["ollama_url"].rstrip("/") + "/api/version"
    with urllib.request.urlopen(url, timeout=5) as r:
        v = json.load(r)
    return f"Ollama {v.get('version', '?')} at {agent.CONFIG['ollama_url']}"


def model_present():
    url = agent.CONFIG["ollama_url"].rstrip("/") + "/api/tags"
    with urllib.request.urlopen(url, timeout=5) as r:
        tags = json.load(r)
    names = [m["name"] for m in tags.get("models", [])]
    want = agent.CONFIG["model"]
    base = want.split(":")[0]
    assert any(n == want or n.split(":")[0] == base for n in names), \
        f"model '{want}' not in {names} - run: ollama pull {want}"
    return want


def tool_sanity():
    out = agent.tool_list_inbox({})
    assert "Sabine" in out or "sabine" in out.lower()
    out = agent.tool_read_context_file({"filename": "pricing-and-leadtimes.md"})
    assert "expedite" in out.lower()
    return "tools read data correctly"


def live_agent_loop():
    """One real agent run: must call at least one tool and produce text."""
    events = list(agent.run_agent(
        "agent", [],
        "What is our standard lead time for stock fittings? Check the pricing file."))
    types = [e["type"] for e in events]
    errors = [e for e in events if e["type"] == "error"]
    assert not errors, errors[0]["text"]
    assert "tool_call" in types, f"model never called a tool (events: {set(types)})"
    text = "".join(e["text"] for e in events if e["type"] == "token")
    assert len(text) > 20, "no meaningful final answer"
    snippet = text.strip().replace("\n", " ")[:90]
    return f'agent called tools and answered: "{snippet}..."'


if __name__ == "__main__":
    print("TWC demo smoke test")
    print(f"model: {agent.CONFIG['model']}\n")
    check("data files", data_files)
    check("Ollama running", ollama_up)
    check("model pulled", model_present)
    check("tool implementations", tool_sanity)
    check("live agent loop (takes 10-60s)", live_agent_loop)
    print()
    if failures:
        print(f"{failures} check(s) failed.")
        sys.exit(1)
    print("All checks passed. Run: python server.py")
