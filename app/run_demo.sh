#!/usr/bin/env bash
# TWC offline demo - DGX Spark launcher
cd "$(dirname "$0")"

if ! curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
  echo "Starting Ollama..."
  ollama serve &
  sleep 4
fi

# Warm the model so the first demo response is fast (loads weights into memory)
MODEL=$(python3 -c "import json;print(json.load(open('config.json'))['model'])")
echo "Warming model: $MODEL (first load can take a minute)..."
curl -s http://localhost:11434/api/generate -d "{\"model\":\"$MODEL\",\"prompt\":\"hi\",\"options\":{\"num_predict\":1}}" > /dev/null

python3 server.py
