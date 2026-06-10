# DGX Spark Setup — TWC Offline Demo

Goal: the Spark runs the whole demo with **zero internet** on demo day. Internet is only needed once, beforehand, to pull the model.

## One-time setup (needs internet — do this at home or on a network that allows it)

1. **Install Ollama** (if not already on the Spark):
   ```
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Pull the model.** Primary and fallback:
   ```
   ollama pull gpt-oss:120b      # primary — strong reasoning + tool use, ~65GB
   ollama pull qwen3:30b         # fallback — ~19GB, very fast
   ```
   The Spark's 128GB unified memory handles either comfortably.

   Why these two: both are mixture-of-experts models, which means only a
   fraction of the model computes per token. On the Spark that translates to
   fast streaming. A dense 70B model (like llama3.3) would be noticeably
   slower on this hardware despite being "smaller" than gpt-oss:120b.

3. **Get the demo app onto the Spark** — see `SPARK-QUICKSTART.md` for the
   git clone walkthrough (preferred), or copy the `app/` folder any way IT
   allows, then `chmod +x run_demo.sh setup.sh`

4. **Set the model** in `app/config.json`:
   ```json
   "model": "gpt-oss:120b"
   ```

5. **Verify Python 3** is present (DGX OS ships with it): `python3 --version`

## Test run (still at home)

```
./run_demo.sh
```

Browser opens at http://localhost:8765. Run all three tabs end to end. Things to check:

- [ ] Chatbot vs. Agent toggle: chatbot says "I don't know your pricing," agent reads the file and answers correctly
- [ ] Morning Workflow: triages all 6 emails, catches the expedite-fee waiver for Sabine River Chemical, drafts land in the outbox
- [ ] Document Analysis: on the invoice, the agent should flag the wrongly-charged expedite fee against the contract waiver
- [ ] Response speed feels demo-appropriate (gpt-oss:120b on the Spark should stream fast)
- [ ] If output quality or speed disappoints, switch config.json to the other model and retest

## Demo day (fully offline)

1. Disconnect from any network (or just never connect — point this out to TWC, it lands well)
2. `./run_demo.sh` — it warms the model so the first response isn't slow
3. Follow `demo-script.md`

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Cannot reach Ollama" in the UI | `ollama serve` in a terminal, then refresh |
| First response very slow | The warmup in run_demo.sh handles this; if skipped, the first query loads the model (~1 min) |
| Model gives weak/odd answers | Switch model in config.json; restart server.py |
| Port 8765 in use | Change "port" in config.json |
| Agent loops or stalls mid-workflow | Hit Reset demo, run again; if persistent, lower num_ctx to 8192 in config.json |
