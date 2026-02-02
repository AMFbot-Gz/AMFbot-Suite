#!/bin/bash

# AMF-OS Sovereign Elite - Hardware-Aware Installer
# Blueprint 2026.1

set -e

echo -e "\033[1;36m🛸 AMF-OS ELITE: Universal Installer Initializing...\033[0m"

# 1. Hardware Kinetic Analysis
VRAM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null || echo "0")
RAM=$(free -m | awk '/^Mem:/{print $2}' 2>/dev/null || sysctl hw.memsize | awk '{print $2/1024/1024}' 2>/dev/null || echo "0")

echo "Kinetic Data: \${VRAM}MB VRAM | \${RAM}MB RAM"

# 2. Optimization Strategy
if [ "\$VRAM" -gt 8000 ]; then
    echo "💎 High-End GPU Detected: Using q8_0 Quantization."
    VERIFY_MODEL="llama4:8b-instruct-q8_0"
else
    echo "🔋 Low-End/Mobile Hardware: Using q4_K_M Quantization."
    VERIFY_MODEL="llama4:8b-instruct-q4_K_M"
fi

# 3. Model Pull Swarm
MODELS=("qwen3:0.5b-instruct-q4_K_M" "\$VERIFY_MODEL" "qwen3:coder")

for model in "\${MODELS[@]}"; do
    echo "🧠 Pulling model: \$model"
    ollama pull "\$model"
done

# 4. Infrastructure Boot
echo "🐋 Deploying Sovereign Infrastructure (Docker/Bun)..."
docker-compose up -d redis lancedb
bun install

echo -e "\033[1;32m✅ AMF-OS SOVEREIGN ELITE DEPLOYED.\033[0m"
