# Spark Quickstart — Zero to Demo in 4 Steps

Step-by-step from a fresh DGX Spark to the demo running. Steps 1–2 need internet **once**. After that the Spark never needs a connection again.

---

## Step 1 — Get the demo onto the Spark (2 minutes)

Open a terminal on the Spark and run:

```
git clone https://github.com/adamloucks1/twc-agentic-demo.git
cd twc-agentic-demo/app
```

No GitHub account needed on the Spark — it's a public download, like any website.

*(No terminal preference? You can also go to the repo page in a browser, click the green **Code** button → **Download ZIP**, extract it, and open a terminal in the `app` folder.)*

## Step 2 — One-command setup (30–60 min, mostly the model download)

```
chmod +x setup.sh && ./setup.sh
```

This installs Ollama if needed, downloads the model (~65GB, the only big download), and writes the config. Get coffee. You only ever do this once.

## Step 3 — Run it

```
./run_demo.sh
```

It warms the model (so the first answer on stage isn't slow) and opens the browser at `http://localhost:8765`. If the browser doesn't open itself, open one and type that address.

## Step 4 — Verify it's demo-ready (10 minutes)

Click through this checklist the first time, and again the morning of the visit:

- [ ] Header shows the green **100% LOCAL** badge and **NVIDIA DGX Spark** badge
- [ ] **Tab 1:** Toggle to "Plain chatbot," ask the Inconel lead-time question — it should NOT know. Toggle to "Agent," same question — it reads the pricing file and answers with real numbers
- [ ] **Tab 1:** Click the third suggestion chip — an email draft appears, written like a machine shop, not like a press release
- [ ] **Tab 2:** Run Morning Workflow — all 6 emails triaged, drafts appear on the right, and the agent catches that Sabine River Chemical's expedite fee should be waived
- [ ] **Tab 3:** Analyze the invoice — it flags the wrongly-charged $1,475.25 expedite fee
- [ ] The ⚡ tokens/sec badge in the header shows a number that feels fast (gpt-oss:120b on the Spark should be comfortably above reading speed)
- [ ] Click **Reset demo** — everything clears

If any output quality feels weak, see "Troubleshooting" in `setup-spark.md` (switching models is a one-line config change).

## Demo day

1. **Don't connect to any network.** That's the point. Mention it.
2. `./run_demo.sh`
3. Click **Reset demo** so the screen is clean
4. Follow `demo-script.md` — it has the full run of show, what to say, and answers for the questions TWC will ask

## Updating the demo later

If Adam's Claude Code setup pushes an update to GitHub, refresh the Spark with:

```
cd twc-agentic-demo && git pull
```

(needs internet for the pull, nothing else changes)
