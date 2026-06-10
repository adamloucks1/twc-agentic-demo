# TWC Offline Agentic AI Demo

**Status:** Loop 1 complete — smoke test + server + streaming verified on Adam's PC (llama3.1:8b, 2026-06-09). Next: Loop 2, deploy to Spark.
**Demo date:** Week of 2026-06-15 (TWC campus visit)
**Hardware:** NVIDIA DGX Spark (128GB unified memory), runs fully offline
**Purpose:** Show Texas Workforce Commission a live agentic AI demonstration supporting the grant partnership for the Agentic AI for Business training program. Lamar's network blocks AI tools, so this runs entirely on local hardware with no internet.

---

## What It Is

A self-contained web app that runs a real LLM locally via Ollama. It simulates the agent a course participant would build: a business agent for **Gulf Coast Machining Co.**, a fictional CNC machine shop in Beaumont serving the petrochemical industry.

Three scenarios, mapped to the course:

| Tab | What TWC sees | Course tie-in |
|---|---|---|
| Business Agent | Chat with an agent that knows the business. Includes a **Chatbot vs. Agent toggle** — flip it off and the same model knows nothing. | Days 1–2 |
| Morning Workflow | One click: agent reads the inbox, triages 6 emails, drafts replies in the company voice, writes an owner summary. Every step visible. | Day 3 |
| Document Analysis | Agent reads an invoice, a safety incident report, or a vendor letter — extracts, summarizes, flags issues. | Practical SMB use |

The right-hand **Agent Activity** panel shows every tool call and reasoning step live — the visual proof of "agent, not chatbot."

## Goal State (demo day)

Double-click `run_demo` on the Spark → browser opens → live demo, no internet, no setup on stage.

## Build Loops

- [x] **Loop 1:** Build app + fictional business data; test on Adam's PC with a small model
- [ ] **Loop 2:** Deploy to the DGX Spark with `gpt-oss:120b`; test speed and output quality, tune prompts
- [ ] **Loop 3:** Dry run against `demo-script.md`; record backup video; final polish

## Distribution

Published at **https://github.com/adamloucks1/twc-agentic-demo** (public). The Spark gets it via `git clone`, no USB, no login — see `SPARK-QUICKSTART.md`. This folder remains the source of truth; after changes here, re-push to that repo so the Spark can `git pull`.

## Files

- `app/` — the demo app (zero pip dependencies, Python stdlib only; needs only Python 3.9+ and Ollama)
- `setup-spark.md` — offline deployment instructions for the DGX Spark
- `demo-script.md` — run-of-show: what to click, what to say, TWC talking points

## Quick Start (any machine with Ollama)

```
ollama pull llama3.1:8b     # small model for local testing
cd app
python server.py
```

Browser opens at http://localhost:8765. Model is set in `app/config.json`.
