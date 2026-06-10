"""Headless quote-builder reliability test. Run: python test_quote.py [model]"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "app"))
import agent

if len(sys.argv) > 1:
    agent.CONFIG["model"] = sys.argv[1]

RFQ = ("Build a quote for this customer request:\n\n"
       "Sabine River Chemical has a plant-down emergency: one replacement "
       "impeller shaft in Inconel 718, about 9 machining hours, material is "
       "$610. They need it inside 48 hours.")

agent.QUOTES.clear()
start = time.time()
errors = []
text_parts = []

for ev in agent.run_agent("quote", [], RFQ):
    if ev["type"] == "tool_call":
        print(f"  [{time.time() - start:5.0f}s] tool: {ev['name']} "
              f"{json.dumps(ev['args'])[:120]}", flush=True)
    elif ev["type"] == "tool_result":
        print(f"          -> {ev['preview'][:100]}".replace("\n", " | "),
              flush=True)
    elif ev["type"] == "token":
        text_parts.append(ev["text"])
    elif ev["type"] == "error":
        errors.append(ev["text"])

print()
print(f"model: {agent.CONFIG['model']}  elapsed: {time.time() - start:.0f}s")
if errors:
    print("ERRORS:", errors)

if not agent.QUOTES:
    print("FAIL: no quote was saved")
    sys.exit(1)

q = agent.QUOTES[0]
print("QUOTE:", json.dumps(q, indent=1))
print()
print("SUMMARY:", "".join(text_parts)[:300])

# Expected: ~9*115 + 610*1.15 = 1736.50, expedite waived per contract,
# valid 10 days (Inconel)
checks = {
    "total in plausible range (1500-2100)": 1500 <= float(q["total"]) <= 2100,
    "expedite fee waived (0)": float(q.get("expedite_fee") or 0) == 0,
    "valid_days is 10 (exotic)": int(q.get("valid_days") or 0) == 10,
    "line items filled": bool(str(q.get("line_items", "")).strip()),
    "lead time filled": bool(str(q.get("lead_time", "")).strip()),
}
print()
failed = 0
for label, ok in checks.items():
    print(("  [ok]  " if ok else "  [MISS]") + " " + label)
    failed += 0 if ok else 1
print()
print("PASS" if failed == 0 else f"{failed} quality check(s) missed "
      "(acceptable on small models; verify on the Spark)")
