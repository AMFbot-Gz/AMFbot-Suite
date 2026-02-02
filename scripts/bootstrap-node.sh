#!/bin/bash

# AMF-OS Sovereign Elite - Remote Node Bootstrapper
# Purpose: Prepare a secondary VPS as an execution worker.

set -e

CYAN='\033[1;36m'
GREEN='\033[1;32m'
NC='\033[0m'

echo -e "${CYAN}📡 AMF-OS: Preparing worker node...${NC}"

# 1. Base dependencies
sudo apt update && sudo apt install -y curl git docker.io docker-compose

# 2. Install Bun
if ! command -v bun &> /dev/null; then
    curl -fsSL https://bun.sh/install | bash
    export PATH="$HOME/.bun/bin:$PATH"
fi

# 3. Install Ollama
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
fi

# 4. Clone & Config
echo -e "${CYAN}📦 Cloning Sovereign Kernel...${NC}"
git clone https://github.com/AMFbot-Gz/AMFbot-Suite.git || cd AMFbot-Suite
cd AMFbot-Suite

# Create node-specific .env
cat <<EOF > .env
OLLAMA_HOST=http://localhost:11434
KERNEL_MODE=worker
MASTER_ID=$(hostname)
LOG_LEVEL=info
EOF

# 5. Bootstrap models
ollama pull qwen3:0.5b-instruct
ollama pull qwen3:coder

echo -e "${GREEN}✅ Worker node is ready.${NC}"
echo "Waiting for Master instructions via SSH/WebSocket..."
