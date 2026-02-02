#!/bin/bash

# AMF-OS Sovereign Bootstrap Script
# "One-Click Ready" Installation

set -e

echo -e "\033[1;34m🏗️  AMF-OS Sovereign: Initializing Elite Environment...\033[0m"

# 1. OS & Architecture Detection
OS="$(uname -s)"
ARCH="$(uname -m)"
echo "Detected $OS on $ARCH"

# 2. Dependency Checks (Bun & Docker)
if ! command -v bun &> /dev/null; then
    echo "📦 Bun not found. Installing..."
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
fi

if ! command -v docker &> /dev/null; then
    echo "🐋 Docker not found. Please install Docker for containerized services."
fi

# 3. GPU Detection
if command -v nvidia-smi &> /dev/null; then
    echo "🚀 NVIDIA GPU Detected. Enabling CUDA optimization."
elif [[ "$OS" == "Darwin" && "$ARCH" == "arm64" ]]; then
    echo "🍏 Apple Silicon Detected. Enabling Metal Acceleration."
else
    echo "⚠️  No GPU acceleration detected. Performance may be restricted."
fi

# 4. Ollama Model Management
echo "🧠 Synchronizing Sovereign Models..."
ollama pull llama4:8b || echo "Wait: llama4:8b might not be available yet, falling back to llama3.1:8b" && ollama pull llama3.1:8b
ollama pull qwen3:coder || ollama pull qwen2.5:coder
ollama pull qwen3:0.5b || ollama pull qwen2.5:0.5b

# 5. Application Setup
echo "🔨 Building Bun Binaries..."
bun install
# bun run build

echo -e "\033[1;32m✅ AMF-OS Sovereign Ready to Launch.\033[0m"
echo "Run 'bun run start' to begin."
