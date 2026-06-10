#!/usr/bin/env bash
# One-command setup for the DGX Spark. Needs internet ONCE (to pull the model).
# After this finishes, the demo runs fully offline forever.
set -e
cd "$(dirname "$0")"

MODEL="gpt-oss:120b"

echo "=== TWC Agentic AI Demo - Spark Setup ==="

# 1. Ollama
if ! command -v ollama > /dev/null 2>&1; then
  echo "[1/4] Installing Ollama..."
  curl -fsSL https://ollama.com/install.sh | sh
else
  echo "[1/4] Ollama already installed: $(ollama --version 2>/dev/null | head -1)"
fi

# 2. Start the Ollama server if it isn't running
if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
  echo "[2/4] Starting Ollama server..."
  ollama serve &
  sleep 4
else
  echo "[2/4] Ollama server already running."
fi

# 3. Pull the model (the big download - ~65GB, one time only)
echo "[3/4] Pulling $MODEL (this is the big one-time download)..."
ollama pull "$MODEL"

# 4. Point the demo at the model and label the hardware
echo "[4/4] Writing config..."
python3 - <<EOF
import json
with open("config.json") as f:
    cfg = json.load(f)
cfg["model"] = "$MODEL"
cfg["num_ctx"] = 16384
cfg["hardware_label"] = "NVIDIA DGX Spark · 128GB unified memory"
with open("config.json", "w") as f:
    json.dump(cfg, f, indent=2)
print("config.json updated:", cfg["model"])
EOF

chmod +x run_demo.sh
echo ""
echo "Setup complete. To run the demo (works fully offline from now on):"
echo "    ./run_demo.sh"
