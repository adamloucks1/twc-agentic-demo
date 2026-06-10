"""Headless workflow reliability test. Run: python test_workflow.py [model]"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "app"))
import agent

if len(sys.argv) > 1:
    agent.CONFIG["model"] = sys.argv[1]

agent.OUTBOX.clear()
start = time.time()
counts = {}
text_parts = []
errors = []

for ev in agent.run_agent(
        "workflow", [],
        "Run the morning email workflow now. Triage the whole inbox, draft "
        "every reply that's needed, check anything against our records, then "
        "give me the owner summary."):
    if ev["type"] == "tool_call":
        counts[ev["name"]] = counts.get(ev["name"], 0) + 1
        print(f"  [{time.time() - start:5.0f}s] tool: {ev['name']} {ev['args']}",
              flush=True)
    elif ev["type"] == "token":
        text_parts.append(ev["text"])
    elif ev["type"] == "error":
        errors.append(ev["text"])

text = "".join(text_parts)
leak = any(s in text for s in ('{"name"', '"parameters"', "read_email(",
                               "save_draft(", "tool_call"))
read_all = counts.get("read_email", 0) >= 6
enough_drafts = len(agent.OUTBOX) >= 4

print(f"model:        {agent.CONFIG['model']}")
print(f"time:         {time.time() - start:.0f}s")
print(f"tool calls:   {counts}")
print(f"drafts saved: {len(agent.OUTBOX)} -> {[d['to'][:40] for d in agent.OUTBOX]}")
print(f"json leakage: {'YES - BAD' if leak else 'none'}")
print(f"errors:       {errors if errors else 'none'}")
print(f"summary tail: ...{text.strip()[-400:]}")
print()
verdict = (not leak) and read_all and enough_drafts and not errors
print("VERDICT:", "PASS" if verdict else "FAIL")
sys.exit(0 if verdict else 1)
